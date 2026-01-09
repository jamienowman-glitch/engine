"""Nexus Routes (E-05)."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Optional

from engines.nexus.schemas import (
    SpaceKey, Scope, NexusIngestRequest, NexusQueryRequest, NexusQueryResult
)
from engines.nexus.service import NexusService
from engines.nexus.lance_store import LanceVectorStore
from engines.common.identity import RequestContext

router = APIRouter(prefix="/nexus/spaces/{space_id}", tags=["nexus"])

# Singleton for P0
_store = LanceVectorStore()
_service = NexusService(store=_store)

def get_service():
    return _service

def get_space_key(
    space_id: str,
    request: Request,
    # In real app, tenant_id comes from RequestContext dependency
    # We simulate it for now or assume header
    x_tenant_id: Optional[str] = "t_unknown"
) -> SpaceKey:

    # Simple extraction for P0
    return SpaceKey(
        scope=Scope.TENANT, # Default
        tenant_id=x_tenant_id,
        env="dev",
        project_id="default",
        surface_id="default",
        space_id=space_id
    )

@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest(
    space_id: str,
    payload: NexusIngestRequest,
    service: NexusService = Depends(get_service),
    # space_key logic usually via dependency
):
    # Manual key construction for P0 demo
    key = SpaceKey(
        scope=Scope.TENANT,
        tenant_id=payload.tenantId, # Payload has tenantId
        env=payload.env,
        project_id="default",
        surface_id="default",
        space_id=space_id
    )

    # Check "Missing Route" simulation
    # If tenant is "t_missing", raise 503
    if key.tenant_id == "t_missing":
        raise HTTPException(
            status_code=503,
            detail={"error": {"code": "nexus_store.missing_route"}}
        )

    task_id = await service.ingest(key, payload)
    return {"task_id": task_id}

@router.post("/query", response_model=NexusQueryResult)
async def query(
    space_id: str,
    payload: NexusQueryRequest,
    include_global: bool = False,
    cursor: Optional[str] = None,
    service: NexusService = Depends(get_service)
):
    key = SpaceKey(
        scope=Scope.TENANT,
        tenant_id=payload.tenantId,
        env=payload.env,
        project_id="default",
        surface_id="default",
        space_id=space_id
    )

    if key.tenant_id == "t_missing":
        raise HTTPException(
            status_code=503,
            detail={"error": {"code": "nexus_store.missing_route"}}
        )

    return await service.query(key, payload, include_global=include_global, cursor=cursor)
