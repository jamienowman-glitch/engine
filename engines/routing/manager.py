"""Routing utilities for backend selection and validation."""
from typing import Any, Optional

from engines.common.identity import RequestContext
from engines.routing.registry import routing_registry, MissingRoutingConfig


# Required resource kinds for Phase 0 mounted services
REQUIRED_RESOURCE_KINDS = [
    "feature_flags",
    "strategy_lock",
    "kpi",
    "budget",
    "maybes",
    "memory",
    "analytics_events",
    "rate_limit",
    "firearms",
    "page_content",
    "seo",
    "realtime_registry",
    "chat_bus",
    "nexus_backend",
    "media_v2_storage",
    "raw_storage",
    "timeline",
]

# Backend types that are NOT allowed in production (fail-fast enforcement)
DISALLOWED_BACKENDS = {"memory", "noop", "local", "tmp", "localhost"}

# Sellable modes where only cloud backends are allowed
SELLABLE_MODES = {"t_system", "enterprise", "saas"}

# Backend classes not allowed in sellable modes
FORBIDDEN_BACKEND_CLASSES = {"filesystem", "in_memory", "memory"}

# Exception for forbidden backend class
class ForbiddenBackendClass(Exception):
    """Raised when a forbidden backend is used in a sellable mode."""
    code = "FORBIDDEN_BACKEND_CLASS"


def startup_validation_check() -> None:
    """Validate all required resource kinds are configured at startup.
    
    This ensures that the application cannot start without properly configured
    routing entries for all mounted services. Fail-fast enforcement prevents
    silent fallbacks to memory/noop/localhost backends in production.
    
    Raises:
        MissingRoutingConfig: If any required resource kind is missing or misconfigured
    """
    registry = routing_registry()
    
    # Check system tenant with default env for startup validation
    # In real deployments, create_app will call this during startup
    for resource_kind in REQUIRED_RESOURCE_KINDS:
        try:
            route = registry.get_route(
                resource_kind,
                tenant_id="t_system",
                env="dev",  # Startup checks dev env as baseline
                project_id=None
            )
            
            if not route:
                raise MissingRoutingConfig(
                    f"Startup validation failed: {resource_kind} not configured in routing registry"
                )
            
            # Reject disallowed backends
            if route.backend_type and route.backend_type.lower() in DISALLOWED_BACKENDS:
                raise ValueError(
                    f"Startup validation failed: {resource_kind} configured with disallowed backend "
                    f"'{route.backend_type}'. Allowed: firestore, redis, s3. "
                    f"Update registry before starting application."
                )
        except MissingRoutingConfig:
            raise
        except Exception as e:
            if "Startup validation failed" in str(e):
                raise
            raise MissingRoutingConfig(
                f"Startup validation error for {resource_kind}: {str(e)}"
            ) from e


def get_route_config(
    resource_kind: str,
    tenant_id: str,
    env: str,
    project_id: Optional[str] = None,
    fail_fast: bool = True,
) -> Optional[dict]:
    """Get backend config for a resource kind, with optional fail-fast.
    
    Args:
        resource_kind: e.g. "feature_flags", "chat_bus"
        tenant_id: tenant scope
        env: deployment env
        project_id: optional project scope
        fail_fast: if True and route missing, raise MissingRoutingConfig
    
    Returns:
        config dict if found, None if not found and fail_fast=False
    
    Raises:
        MissingRoutingConfig if fail_fast=True and route not found
    """
    registry = routing_registry()
    route = registry.get_route(resource_kind, tenant_id, env, project_id)
    
    if not route:
        msg = f"Missing routing config for {resource_kind} (tenant={tenant_id}, env={env}, project={project_id})"
        if fail_fast:
            raise MissingRoutingConfig(msg)
        return None
    
    return route.config or {}



def get_backend_type(
    resource_kind: str,
    tenant_id: str,
    env: str,
    project_id: Optional[str] = None,
    fail_fast: bool = True,
) -> Optional[str]:
    """Get backend type for a resource kind.
    
    Args:
        resource_kind: e.g. "feature_flags", "chat_bus"
        tenant_id: tenant scope
        env: deployment env
        project_id: optional project scope
        fail_fast: if True, raise on missing
    
    Returns:
        backend_type string if found, None otherwise
    
    Raises:
        MissingRoutingConfig if fail_fast=True and route not found
    """
    registry = routing_registry()
    route = registry.get_route(resource_kind, tenant_id, env, project_id)
    
    if not route:
        if fail_fast:
            msg = f"Missing routing config for {resource_kind}"
            raise MissingRoutingConfig(msg)
        return None
    
    return route.backend_type


def resolve_backend_with_guard(
    resource_kind: str,
    backend_type: Optional[str],
    context: RequestContext,
) -> None:
    """Guard: enforce cloud-only backends in sellable modes (Phase 0.5 Lane 2).
    
    Lab-only enforcement: filesystem and in-memory backends are forbidden
    when running in production modes (t_system, enterprise, saas).
    
    Args:
        resource_kind: e.g. "event_stream", "object_store"
        backend_type: resolved backend (e.g., "filesystem", "firestore", "s3")
        context: RequestContext with mode/tenant/env/project
    
    Raises:
        ForbiddenBackendClass: if backend is filesystem/in-memory in sellable mode
    
    Example:
        >>> route = registry.get_route("event_stream", "t_demo", "dev")
        >>> if route:
        ...     resolve_backend_with_guard("event_stream", route.backend_type, context)
    """
    if not backend_type:
        return  # No backend type, nothing to guard
    
    backend_lower = backend_type.lower()
    mode_lower = (context.mode or "lab").lower()
    
    # Check if we're in a sellable mode with a forbidden backend
    if mode_lower in SELLABLE_MODES and backend_lower in FORBIDDEN_BACKEND_CLASSES:
        raise ForbiddenBackendClass(
            f"[{ForbiddenBackendClass.code}] Backend '{backend_type}' is forbidden in mode '{context.mode}' "
            f"(resource_kind={resource_kind}, tenant={context.tenant_id}, env={context.env}). "
            f"Sellable modes require cloud backends (firestore, s3, dynamodb, cosmos, etc.). "
            f"Use 'lab' mode for filesystem/in-memory backends."
        )
