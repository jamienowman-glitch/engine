"""FastAPI routes for flow/graph/overlay persistence (Agent B)."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import get_auth_context, require_tenant_membership
from engines.persistence.models import ArtifactCreateRequest, ArtifactRecord, ArtifactUpdateRequest
from engines.persistence.service import ArtifactPersistenceService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["persistence"])


def _service(context: RequestContext, store_name: str) -> ArtifactPersistenceService:
    try:
        return ArtifactPersistenceService(context, store_name)
    except RuntimeError as exc:
        # Warning-first then block per Agent B contract
        logger.warning("Routing missing for %s: %s", store_name, exc)
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ===== Flows =====

@router.post("/flows", response_model=ArtifactRecord)
def create_flow(
    payload: ArtifactCreateRequest,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    try:
        return _service(context, "flow_store").create(payload)
    except ValueError as exc:
        if str(exc) == "record_exists":
            raise HTTPException(status_code=409, detail="flow_exists") from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/flows", response_model=list[ArtifactRecord])
def list_flows(
    surface_id: Optional[str] = None,
    include_deleted: bool = Query(False),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    return _service(context, "flow_store").list(surface_id=surface_id, include_deleted=include_deleted)


@router.get("/flows/{flow_id}", response_model=ArtifactRecord)
def get_flow(
    flow_id: str,
    version: Optional[int] = Query(None),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    try:
        return _service(context, "flow_store").get(flow_id, version=version)
    except KeyError:
        raise HTTPException(status_code=404, detail="flow_not_found")


@router.put("/flows/{flow_id}", response_model=ArtifactRecord)
def update_flow(
    flow_id: str,
    payload: ArtifactUpdateRequest,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    try:
        return _service(context, "flow_store").update(flow_id, payload)
    except KeyError:
        raise HTTPException(status_code=404, detail="flow_not_found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/flows/{flow_id}", response_model=ArtifactRecord)
def delete_flow(
    flow_id: str,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    try:
        return _service(context, "flow_store").delete(flow_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="flow_not_found")


# ===== Graphs =====

@router.post("/graphs", response_model=ArtifactRecord)
def create_graph(
    payload: ArtifactCreateRequest,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    try:
        return _service(context, "graph_store").create(payload)
    except ValueError as exc:
        if str(exc) == "record_exists":
            raise HTTPException(status_code=409, detail="graph_exists") from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/graphs", response_model=list[ArtifactRecord])
def list_graphs(
    surface_id: Optional[str] = None,
    include_deleted: bool = Query(False),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    return _service(context, "graph_store").list(surface_id=surface_id, include_deleted=include_deleted)


@router.get("/graphs/{graph_id}", response_model=ArtifactRecord)
def get_graph(
    graph_id: str,
    version: Optional[int] = Query(None),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    try:
        return _service(context, "graph_store").get(graph_id, version=version)
    except KeyError:
        raise HTTPException(status_code=404, detail="graph_not_found")


@router.put("/graphs/{graph_id}", response_model=ArtifactRecord)
def update_graph(
    graph_id: str,
    payload: ArtifactUpdateRequest,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    try:
        return _service(context, "graph_store").update(graph_id, payload)
    except KeyError:
        raise HTTPException(status_code=404, detail="graph_not_found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/graphs/{graph_id}", response_model=ArtifactRecord)
def delete_graph(
    graph_id: str,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    try:
        return _service(context, "graph_store").delete(graph_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="graph_not_found")


# ===== Overlays =====

@router.post("/overlays", response_model=ArtifactRecord)
def create_overlay(
    payload: ArtifactCreateRequest,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    try:
        return _service(context, "overlay_store").create(payload)
    except ValueError as exc:
        if str(exc) == "record_exists":
            raise HTTPException(status_code=409, detail="overlay_exists") from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/overlays", response_model=list[ArtifactRecord])
def list_overlays(
    surface_id: Optional[str] = None,
    include_deleted: bool = Query(False),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    return _service(context, "overlay_store").list(surface_id=surface_id, include_deleted=include_deleted)


@router.get("/overlays/{overlay_id}", response_model=ArtifactRecord)
def get_overlay(
    overlay_id: str,
    version: Optional[int] = Query(None),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    try:
        return _service(context, "overlay_store").get(overlay_id, version=version)
    except KeyError:
        raise HTTPException(status_code=404, detail="overlay_not_found")


@router.put("/overlays/{overlay_id}", response_model=ArtifactRecord)
def update_overlay(
    overlay_id: str,
    payload: ArtifactUpdateRequest,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    try:
        return _service(context, "overlay_store").update(overlay_id, payload)
    except KeyError:
        raise HTTPException(status_code=404, detail="overlay_not_found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/overlays/{overlay_id}", response_model=ArtifactRecord)
def delete_overlay(
    overlay_id: str,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    try:
        return _service(context, "overlay_store").delete(overlay_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="overlay_not_found")
