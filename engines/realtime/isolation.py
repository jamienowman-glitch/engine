"""Tenant Isolation and Routing Validation."""
from __future__ import annotations

import logging
import os
from typing import Dict, Optional, Protocol

from fastapi import HTTPException
from engines.common.identity import RequestContext
from engines.config import runtime_config
from engines.realtime.contracts import RoutingKeys

try:  # pragma: no cover - optional dependency
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover
    firestore = None

logger = logging.getLogger(__name__)

_VALID_ENV_ALIASES = {"dev", "staging", "prod"}


def _normalize_env_for_validation(value: str) -> str:
    env_norm = value.lower()
    if env_norm == "stage":
        env_norm = "staging"
    if env_norm not in _VALID_ENV_ALIASES:
        raise ValueError(f"unsupported env '{value}' in routing keys")
    return env_norm


class ResourceRegistry(Protocol):
    def register_thread(self, tenant_id: str, thread_id: str) -> None: ...
    def register_canvas(self, tenant_id: str, canvas_id: str) -> None: ...
    def get_thread_tenant(self, thread_id: str) -> Optional[str]: ...
    def get_canvas_tenant(self, canvas_id: str) -> Optional[str]: ...
    def clear(self) -> None: ...


class InMemoryResourceRegistry:
    def __init__(self) -> None:
        self._threads: Dict[str, str] = {}
        self._canvases: Dict[str, str] = {}

    def register_thread(self, tenant_id: str, thread_id: str) -> None:
        self._threads[thread_id] = tenant_id

    def register_canvas(self, tenant_id: str, canvas_id: str) -> None:
        self._canvases[canvas_id] = tenant_id

    def get_thread_tenant(self, thread_id: str) -> Optional[str]:
        return self._threads.get(thread_id)

    def get_canvas_tenant(self, canvas_id: str) -> Optional[str]:
        return self._canvases.get(canvas_id)

    def clear(self) -> None:
        self._threads.clear()
        self._canvases.clear()


class FirestoreResourceRegistry:
    _collection = "realtime_registry"

    def __init__(self, client: Optional[object] = None) -> None:
        if firestore is None:
            raise RuntimeError("google-cloud-firestore is required for realtime registry persistence")
        project = runtime_config.get_firestore_project()
        if not project:
            raise RuntimeError("GCP project is required for Firestore realtime registry")
        self._client = client or firestore.Client(project=project)  # type: ignore[arg-type]

    def _doc(self, resource_type: str, resource_id: str):
        doc_id = f"{resource_type}__{resource_id}"
        return self._client.collection(self._collection).document(doc_id)

    def register_thread(self, tenant_id: str, thread_id: str) -> None:
        self._doc("thread", thread_id).set({"tenant_id": tenant_id})

    def register_canvas(self, tenant_id: str, canvas_id: str) -> None:
        self._doc("canvas", canvas_id).set({"tenant_id": tenant_id})

    def _get_tenant(self, resource_type: str, resource_id: str) -> Optional[str]:
        snap = self._doc(resource_type, resource_id).get()
        if not snap or not getattr(snap, "exists", False):
            return None
        return snap.to_dict().get("tenant_id")

    def get_thread_tenant(self, thread_id: str) -> Optional[str]:
        return self._get_tenant("thread", thread_id)

    def get_canvas_tenant(self, canvas_id: str) -> Optional[str]:
        return self._get_tenant("canvas", canvas_id)

    def clear(self) -> None:
        raise NotImplementedError("Firestore registry cannot be cleared in production")


def _default_registry() -> ResourceRegistry:
    backend = (os.getenv("REALTIME_REGISTRY_BACKEND") or "memory").lower()
    if backend == "firestore":
        try:
            return FirestoreResourceRegistry()
        except Exception as exc:
            logger.warning("Firestore registry unavailable: %s", exc)
    return InMemoryResourceRegistry()


registry: ResourceRegistry = _default_registry()


def get_registry() -> ResourceRegistry:
    return registry


def set_registry(instance: ResourceRegistry) -> None:
    global registry
    registry = instance

# --- Registry Helpers (Exposed for Tests) ---

def register_thread_resource(tenant_id: str, thread_id: str) -> Optional[str]:
    """
    Register a thread and return the recorded owner (used by tests/fixtures).
    """
    registry.register_thread(tenant_id, thread_id)
    return registry.get_thread_tenant(thread_id)


def register_canvas_resource(tenant_id: str, canvas_id: str) -> Optional[str]:
    """
    Register a canvas and return the recorded owner (used by tests/fixtures).
    """
    registry.register_canvas(tenant_id, canvas_id)
    return registry.get_canvas_tenant(canvas_id)


# --- Validation Logic ---

def validate_routing(ctx: RequestContext, routing: RoutingKeys) -> None:
    """
    Assert that the routing keys match the request context (tenant/env).
    """
    if routing.tenant_id != ctx.tenant_id:
        raise HTTPException(
            status_code=403, 
            detail=f"Routing mismatch: tenant '{routing.tenant_id}' != '{ctx.tenant_id}'"
        )

    try:
        routing_env = _normalize_env_for_validation(routing.env)
        ctx_env = _normalize_env_for_validation(ctx.env)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    if routing_env != ctx_env:
        raise HTTPException(
            status_code=403,
            detail=f"Routing mismatch: env '{routing.env}' != '{ctx.env}'"
        )
    
    # Ideally verify more if context has user info


def verify_thread_access(tenant_id: str, thread_id: str) -> None:
    """
    Verify thread belongs to tenant.
    Raises 403/404 if mismatch or unknown.
    """
    owner = registry.get_thread_tenant(thread_id)
    if owner is None:
        # If thread doesn't exist in registry, acts as 404.
        # However, for transition, we might be permissive or strict.
        # Spec says: "No TODO verify thread belongs to tenant left unfixed."
        # So we must be strict or have a clear fallback.
        # FALLBACK: If registry is empty (dev mode), we might log warning.
        # BUT spec says "Full Gas".
        # We will assume for now that if it's not in registry, it's NOT ACCESSIBLE.
        # But to allow "creating" threads implicitly in dev, we might need a distinct "create" step.
        # Let's be semi-strict: if known, must match. If unknown, 404.
        # Wait, if I start a fresh server I can't connect?
        # Tests need to register threads.
        logger.warning(f"Accessing unknown thread {thread_id}. Denying strict isolation.")
        raise HTTPException(status_code=404, detail="Thread not found")
    
    if owner != tenant_id:
        # Obfuscate existence across tenants? 403 or 404?
        # 403 leaks ID existence. 404 is safer.
        raise HTTPException(status_code=404, detail="Thread not found")


def verify_canvas_access(tenant_id: str, canvas_id: str) -> None:
    """
    Verify canvas belongs to tenant.
    """
    owner = registry.get_canvas_tenant(canvas_id)
    if owner is None:
        logger.warning(f"Accessing unknown canvas {canvas_id}. Denying strict isolation.")
        raise HTTPException(status_code=404, detail="Canvas not found")
    
    if owner != tenant_id:
        raise HTTPException(status_code=404, detail="Canvas not found")
