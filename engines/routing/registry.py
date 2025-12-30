"""Routing registry for backend selection (resource_kind -> backend config).

Lane 3 — Control-plane data-driven backend routing. Persistent, tenant/env/project-aware.
No behavior/business logic changes; only backend selection/validation.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Protocol

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ===== Models =====

class ResourceRoute(BaseModel):
    """Control-plane record mapping resource_kind to backend config (tenant/env/project aware).
    
    resource_kind: service identifier (e.g., "feature_flags", "chat_bus", "raw_storage")
    tenant_id: owning tenant (e.g., "t_system" for global, "t_acme" for single-tenant routes)
    env: deployment env (e.g., "dev", "staging", "prod")
    project_id: optional project scope
    backend_type: backend name (e.g., "firestore", "redis", "memory" for tests only)
    config: backend-specific config dict (host, port, bucket, credentials, etc.)
    required: whether missing config should raise or allow fallback (should be True for prod)
    created_at, updated_at: timestamps
    """
    id: str
    resource_kind: str
    tenant_id: str
    env: str
    project_id: Optional[str] = None
    backend_type: str
    config: Dict[str, Any] = Field(default_factory=dict)
    required: bool = True
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class MissingRoutingConfig(Exception):
    """Raised when required routing config is missing."""
    pass


# ===== Repository Protocol =====

class RoutingRegistry(Protocol):
    """Storage abstraction for resource routing."""

    def upsert_route(self, route: ResourceRoute) -> ResourceRoute: ...
    def get_route(self, resource_kind: str, tenant_id: str, env: str, project_id: Optional[str] = None) -> Optional[ResourceRoute]: ...
    def list_routes(self, resource_kind: Optional[str] = None, tenant_id: Optional[str] = None) -> list[ResourceRoute]: ...
    def delete_route(self, resource_kind: str, tenant_id: str, env: str, project_id: Optional[str] = None) -> None: ...


# ===== In-Memory Implementation =====

class InMemoryRoutingRegistry:
    """In-memory routing registry for dev/tests."""

    def __init__(self):
        self._routes: Dict[tuple, ResourceRoute] = {}

    def _key(self, resource_kind: str, tenant_id: str, env: str, project_id: Optional[str] = None) -> tuple:
        return (resource_kind, tenant_id, env, project_id or "")

    def upsert_route(self, route: ResourceRoute) -> ResourceRoute:
        key = self._key(route.resource_kind, route.tenant_id, route.env, route.project_id)
        self._routes[key] = route
        return route

    def get_route(self, resource_kind: str, tenant_id: str, env: str, project_id: Optional[str] = None) -> Optional[ResourceRoute]:
        key = self._key(resource_kind, tenant_id, env, project_id)
        return self._routes.get(key)

    def list_routes(self, resource_kind: Optional[str] = None, tenant_id: Optional[str] = None) -> list[ResourceRoute]:
        results = list(self._routes.values())
        if resource_kind:
            results = [r for r in results if r.resource_kind == resource_kind]
        if tenant_id:
            results = [r for r in results if r.tenant_id == tenant_id]
        return results

    def delete_route(self, resource_kind: str, tenant_id: str, env: str, project_id: Optional[str] = None) -> None:
        key = self._key(resource_kind, tenant_id, env, project_id)
        self._routes.pop(key, None)


# ===== Firestore Implementation =====

class FirestoreRoutingRegistry:
    """Firestore-backed routing registry.
    
    Collection: routing_registry/{id}
    """

    def __init__(self, client: Optional[Any] = None):
        try:
            from google.cloud import firestore  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("google-cloud-firestore not installed") from exc
        from engines.config import runtime_config

        project = runtime_config.get_firestore_project()
        if not project:
            raise RuntimeError("GCP project required for Firestore routing registry")
        self._client = client or firestore.Client(project=project)  # type: ignore[arg-type]
        self._collection = "routing_registry"

    def upsert_route(self, route: ResourceRoute) -> ResourceRoute:
        self._client.collection(self._collection).document(route.id).set(route.model_dump())
        return route

    def get_route(self, resource_kind: str, tenant_id: str, env: str, project_id: Optional[str] = None) -> Optional[ResourceRoute]:
        docs = (
            self._client.collection(self._collection)
            .where("resource_kind", "==", resource_kind)
            .where("tenant_id", "==", tenant_id)
            .where("env", "==", env)
        )
        if project_id:
            docs = docs.where("project_id", "==", project_id)
        else:
            docs = docs.where("project_id", "==", None)
        
        for d in docs.limit(1).stream():
            return ResourceRoute(**d.to_dict())
        return None

    def list_routes(self, resource_kind: Optional[str] = None, tenant_id: Optional[str] = None) -> list[ResourceRoute]:
        query = self._client.collection(self._collection)
        if resource_kind:
            query = query.where("resource_kind", "==", resource_kind)
        if tenant_id:
            query = query.where("tenant_id", "==", tenant_id)
        return [ResourceRoute(**d.to_dict()) for d in query.stream()]

    def delete_route(self, resource_kind: str, tenant_id: str, env: str, project_id: Optional[str] = None) -> None:
        docs = (
            self._client.collection(self._collection)
            .where("resource_kind", "==", resource_kind)
            .where("tenant_id", "==", tenant_id)
            .where("env", "==", env)
        )
        if project_id:
            docs = docs.where("project_id", "==", project_id)
        else:
            docs = docs.where("project_id", "==", None)
        
        for d in docs.stream():
            d.reference.delete()


# ===== Global singleton =====

_routing_registry: Optional[RoutingRegistry] = None


def routing_registry() -> RoutingRegistry:
    """Get or initialize the routing registry singleton.
    
    GAP-G2: Enforce durable routing registry in production.
    - In production: requires ROUTING_REGISTRY_BACKEND=firestore
    - In tests: explicitly set via set_routing_registry() before use
    - Prevents silent fallback to InMemory in prod paths
    """
    global _routing_registry
    if _routing_registry is None:
        backend = os.getenv("ROUTING_REGISTRY_BACKEND", "").lower()
        
        # Phase 0 closeout: fail-fast if no durable registry configured
        if backend == "firestore":
            _routing_registry = FirestoreRoutingRegistry()
        elif backend == "memory":
            _routing_registry = InMemoryRoutingRegistry()
        elif not backend:
            # InMemory only allowed if explicitly configured (tests)
            # Production requires explicit ROUTING_REGISTRY_BACKEND=firestore
            raise MissingRoutingConfig(
                "ROUTING_REGISTRY_BACKEND not set. "
                "Production requires ROUTING_REGISTRY_BACKEND=firestore. "
                "Tests must explicitly call set_routing_registry() before using routing_registry()."
            )
        else:
            raise MissingRoutingConfig(
                f"Unsupported ROUTING_REGISTRY_BACKEND={backend}. "
                f"Only 'firestore' is allowed for production. "
                f"Tests must use set_routing_registry()."
            )
    return _routing_registry


def set_routing_registry(registry: RoutingRegistry) -> None:
    """Set the routing registry (for testing)."""
    global _routing_registry
    _routing_registry = registry
