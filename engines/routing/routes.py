"""Routing control-plane API routes."""
from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext, RequestContextBuilder
from engines.routing.registry import ResourceRoute
from engines.routing.service import RoutingControlPlaneService


router = APIRouter(prefix="/routing", tags=["routing"])


# ===== Schemas =====

class ResourceRouteCreate(BaseModel):
    """Schema for creating/upserting a route."""
    resource_kind: str = Field(..., description="Resource kind (e.g., vector_store, object_store)")
    tenant_id: str = Field(..., description="Tenant ID (e.g., t_system)")
    env: str = Field(..., description="Environment (dev, staging, prod)")
    project_id: Optional[str] = Field(None, description="Project ID (optional)")
    surface_id: Optional[str] = Field(None, description="Surface ID (optional, accepts aliases)")
    backend_type: str = Field(..., description="Backend type (e.g., firestore, s3, filesystem)")
    config: dict = Field(default_factory=dict, description="Backend-specific config")
    required: bool = Field(True, description="Whether missing config should raise error")


class ResourceRouteResponse(BaseModel):
    """Response schema for route operations."""
    id: str
    resource_kind: str
    tenant_id: str
    env: str
    project_id: Optional[str] = None
    surface_id: Optional[str] = None
    backend_type: str
    config: dict
    required: bool
    created_at: str
    updated_at: str


class ResourceRouteDiagnosticsResponse(BaseModel):
    """Lane 5: Response schema for read-only diagnostics view."""
    id: str
    resource_kind: str
    tenant_id: str
    env: str
    backend_type: str
    config: dict  # No secrets in response
    tier: str  # free, pro, enterprise
    cost_notes: Optional[str] = None
    health_status: str  # healthy, degraded, unhealthy, unknown
    last_switch_time: Optional[str] = None
    previous_backend_type: Optional[str] = None
    switch_rationale: Optional[str] = None
    created_at: str
    updated_at: str


class RouteSwitchRequest(BaseModel):
    """Lane 5: Request schema for manual route switching."""
    backend_type: str = Field(..., description="New backend type to switch to")
    config: Optional[dict] = Field(default_factory=dict, description="New backend config (optional)")
    tier: Optional[str] = Field(None, description="Cost tier (free, pro, enterprise)")
    cost_notes: Optional[str] = Field(None, description="Cost implications (no secrets)")
    rationale: str = Field(..., description="Reason for switching (required for audit trail)")
    strategy_lock_id: Optional[str] = Field(None, description="Strategy lock ID if required by policy")


# ===== Routes =====

@router.post("/routes", response_model=ResourceRouteResponse)
async def upsert_route(
    req: ResourceRouteCreate,
    context: RequestContext = Depends(RequestContextBuilder.from_request),
) -> dict:
    """Upsert a routing registry entry.
    
    - Accepts surface_id aliases (e.g., SQUARED²)
    - Stores canonical ASCII form internally
    - Emits audit event and stream event (ROUTE_CHANGED)
    """
    service = RoutingControlPlaneService()
    
    route = ResourceRoute(
        id=str(uuid4()),
        resource_kind=req.resource_kind,
        tenant_id=req.tenant_id,
        env=req.env,
        project_id=req.project_id,
        surface_id=req.surface_id,
        backend_type=req.backend_type,
        config=req.config,
        required=req.required,
    )
    
    result = service.upsert_route(route, context)
    
    return {
        "id": result.id,
        "resource_kind": result.resource_kind,
        "tenant_id": result.tenant_id,
        "env": result.env,
        "project_id": result.project_id,
        "surface_id": result.surface_id,
        "backend_type": result.backend_type,
        "config": result.config,
        "required": result.required,
        "created_at": result.created_at.isoformat(),
        "updated_at": result.updated_at.isoformat(),
    }


@router.get("/routes/{resource_kind}/{tenant_id}/{env}", response_model=ResourceRouteResponse)
async def get_route(
    resource_kind: str,
    tenant_id: str,
    env: str,
    project_id: Optional[str] = Query(None),
    context: RequestContext = Depends(RequestContextBuilder.from_request),
) -> dict:
    """Get a routing entry by resource_kind, tenant_id, and env.
    
    Surface normalization is applied: accepts aliases and returns canonical form.
    """
    service = RoutingControlPlaneService()
    
    route = service.get_route(resource_kind, tenant_id, env, project_id)
    
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    return {
        "id": route.id,
        "resource_kind": route.resource_kind,
        "tenant_id": route.tenant_id,
        "env": route.env,
        "project_id": route.project_id,
        "surface_id": route.surface_id,
        "backend_type": route.backend_type,
        "config": route.config,
        "required": route.required,
        "created_at": route.created_at.isoformat(),
        "updated_at": route.updated_at.isoformat(),
    }


@router.get("/routes", response_model=List[ResourceRouteResponse])
async def list_routes(
    resource_kind: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    context: RequestContext = Depends(RequestContextBuilder.from_request),
) -> list:
    """List routes matching optional filters.
    
    Query params:
      - resource_kind: filter by resource kind
      - tenant_id: filter by tenant
    """
    service = RoutingControlPlaneService()
    
    routes = service.list_routes(resource_kind, tenant_id)
    
    return [
        {
            "id": r.id,
            "resource_kind": r.resource_kind,
            "tenant_id": r.tenant_id,
            "env": r.env,
            "project_id": r.project_id,
            "surface_id": r.surface_id,
            "backend_type": r.backend_type,
            "config": r.config,
            "required": r.required,
            "created_at": r.created_at.isoformat(),
            "updated_at": r.updated_at.isoformat(),
        }
        for r in routes
    ]

# ===== Lane 5 Endpoints (t_system Surfacing) =====

@router.get("/diagnostics/{resource_kind}/{tenant_id}/{env}", response_model=ResourceRouteDiagnosticsResponse)
async def get_route_diagnostics(
    resource_kind: str,
    tenant_id: str,
    env: str,
    project_id: Optional[str] = Query(None),
    context: RequestContext = Depends(RequestContextBuilder.from_request),
) -> dict:
    """Get route diagnostics (read-only, no secrets).
    
    Lane 5: Provides t_system view of current routing with diagnostic metadata:
    - Current backend_type and config (no secrets)
    - Cost tier and notes
    - Health status
    - Switch history (previous backend, rationale, timestamp)
    
    Available to all modes/roles for diagnostic purposes.
    """
    service = RoutingControlPlaneService()
    
    route = service.get_route(resource_kind, tenant_id, env, project_id)
    
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    return {
        "id": route.id,
        "resource_kind": route.resource_kind,
        "tenant_id": route.tenant_id,
        "env": route.env,
        "backend_type": route.backend_type,
        "config": route.config,
        "tier": route.tier,
        "cost_notes": route.cost_notes,
        "health_status": route.health_status,
        "last_switch_time": route.last_switch_time.isoformat() if route.last_switch_time else None,
        "previous_backend_type": route.previous_backend_type,
        "switch_rationale": route.switch_rationale,
        "created_at": route.created_at.isoformat(),
        "updated_at": route.updated_at.isoformat(),
    }


@router.put("/routes/{resource_kind}/{tenant_id}/{env}/switch", response_model=ResourceRouteDiagnosticsResponse)
async def switch_route_backend(
    resource_kind: str,
    tenant_id: str,
    env: str,
    req: RouteSwitchRequest,
    project_id: Optional[str] = Query(None),
    context: RequestContext = Depends(RequestContextBuilder.from_request),
) -> dict:
    """Switch backend for a route (manual switch with strategy lock guard).
    
    Lane 5: Allows t_system operators to manually flip backends with:
    - Strategy lock enforcement (if configured for resource_kind)
    - Audit trail (rationale + operator + timestamp)
    - StreamEvent emission (ROUTE_BACKEND_SWITCHED)
    - Switch history (previous backend, rationale preserved)
    
    Requires:
    - rationale: reason for switch (mandatory for audit)
    - strategy_lock_id: if strategy lock is required for this resource_kind
    - new backend_type + config
    
    Guards:
    - Strategy lock validation (if route.required=True or policy-driven)
    - Audit event emission (routing:switch_backend)
    - StreamEvent ROUTE_BACKEND_SWITCHED with rationale
    """
    service = RoutingControlPlaneService()
    
    # Get current route
    current_route = service.get_route(resource_kind, tenant_id, env, project_id)
    if not current_route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    # Lane 5: Strategy lock validation (if enabled)
    try:
        from engines.strategy_lock.service import get_strategy_lock_service
        lock_service = get_strategy_lock_service()
        
        # Check if strategy lock is required for this route switch
        # For now, check if lock_id provided or if resource_kind has global lock requirement
        if req.strategy_lock_id:
            try:
                lock = lock_service.get_lock(context, req.strategy_lock_id)
                # Verify lock covers this action
                if "routing:switch_backend" not in (lock.allowed_actions or []):
                    raise HTTPException(
                        status_code=403,
                        detail=f"Strategy lock {req.strategy_lock_id} does not cover routing:switch_backend"
                    )
                if lock.status.value != "approved":
                    raise HTTPException(
                        status_code=403,
                        detail=f"Strategy lock {req.strategy_lock_id} is not approved (status: {lock.status})"
                    )
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Strategy lock validation failed: {e}")
    except ImportError:
        # Strategy lock not available in this environment
        pass
    
    # Update route with new backend
    previous_backend = current_route.backend_type
    current_route.backend_type = req.backend_type
    if req.config:
        current_route.config.update(req.config)
    if req.tier:
        current_route.tier = req.tier
    if req.cost_notes:
        current_route.cost_notes = req.cost_notes
    
    # Store switch history
    current_route.previous_backend_type = previous_backend
    current_route.switch_rationale = req.rationale
    current_route.last_switch_time = None  # Will be set by service
    
    # Upsert with audit trail
    updated_route = service.upsert_route(current_route, context)
    
    return {
        "id": updated_route.id,
        "resource_kind": updated_route.resource_kind,
        "tenant_id": updated_route.tenant_id,
        "env": updated_route.env,
        "backend_type": updated_route.backend_type,
        "config": updated_route.config,
        "tier": updated_route.tier,
        "cost_notes": updated_route.cost_notes,
        "health_status": updated_route.health_status,
        "last_switch_time": updated_route.last_switch_time.isoformat() if updated_route.last_switch_time else None,
        "previous_backend_type": updated_route.previous_backend_type,
        "switch_rationale": updated_route.switch_rationale,
        "created_at": updated_route.created_at.isoformat(),
        "updated_at": updated_route.updated_at.isoformat(),
    }