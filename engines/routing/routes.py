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
