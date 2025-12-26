"""Routing utilities for backend selection and validation."""
from typing import Any, Optional

from engines.routing.registry import routing_registry, MissingRoutingConfig


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
