"""FastAPI routes for Notes / Maybes."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from engines.common.error_envelope import error_response
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import get_auth_context, require_tenant_membership
from engines.nexus.hardening.gate_chain import GateChain, get_gate_chain
from engines.maybes.schemas import MaybeCreate, MaybeQuery, MaybeUpdate
from engines.maybes.service import MaybesError, MaybesNotFound, MaybesService

router = APIRouter(tags=["notes"])
service = MaybesService()


def _parse_tags(tags: Optional[str]) -> list[str] | None:
    if tags is None:
        return None
    parts = [t for t in (tags.split(",") if isinstance(tags, str) else []) if t]
    return parts or None


def _enforce_gate(gate_chain: GateChain, ctx: RequestContext, action: str):
    try:
        gate_chain.run(ctx=ctx, action=action, resource_kind="maybe_note")
    except HTTPException as exc:
        raise exc


@router.post("/notes")
@router.post("/maybes/items")
def create_note(
    req: MaybeCreate,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
    gate_chain: GateChain = Depends(get_gate_chain),
):
    require_tenant_membership(auth, context.tenant_id)
    _enforce_gate(gate_chain, context, "maybes_create")
    try:
        return service.create_item(req, context)
    except MaybesNotFound as exc:
        return error_response(code="maybes.not_found", message=str(exc), status_code=404)
    except MaybesError as exc:
        return error_response(code="maybes.invalid_request", message=str(exc), status_code=400)
    except RuntimeError as exc:
        return error_response(code="maybes.service_unavailable", message=str(exc), status_code=503)
    except Exception as exc:
        return error_response(code="maybes.create_failed", message=str(exc), status_code=500)


@router.get("/notes")
@router.get("/maybes/items")
def list_notes(
    surface_id: Optional[str] = None,
    project_id: Optional[str] = None,
    user_id: Optional[str] = None,
    tags_any: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    query = MaybeQuery(
        surface_id=surface_id or context.surface_id,
        project_id=project_id or context.project_id,
        user_id=user_id or context.user_id,
        tags_any=_parse_tags(tags_any),
        limit=limit,
        offset=offset,
    )
    try:
        items = service.list_items(context, query)
        return {"items": items}
    except MaybesError as exc:
        return error_response(code="maybes.query_failed", message=str(exc), status_code=400)
    except RuntimeError as exc:
        return error_response(code="maybes.service_unavailable", message=str(exc), status_code=503)


@router.get("/notes/{item_id}")
@router.get("/maybes/items/{item_id}")
def get_note(
    item_id: str,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    try:
        return service.get_item(context, item_id)
    except MaybesNotFound as exc:
        return error_response(code="maybes.not_found", message=str(exc), status_code=404)
    except RuntimeError as exc:
        return error_response(code="maybes.service_unavailable", message=str(exc), status_code=503)


@router.put("/notes/{item_id}")
@router.patch("/maybes/items/{item_id}")
def update_note(
    item_id: str,
    req: MaybeUpdate,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
    gate_chain: GateChain = Depends(get_gate_chain),
):
    require_tenant_membership(auth, context.tenant_id)
    _enforce_gate(gate_chain, context, "maybes_update")
    try:
        return {"item": service.update_item(context, item_id, req)}
    except MaybesNotFound as exc:
        return error_response(code="maybes.not_found", message=str(exc), status_code=404)
    except MaybesError as exc:
        return error_response(code="maybes.invalid_update", message=str(exc), status_code=400)
    except RuntimeError as exc:
        return error_response(code="maybes.service_unavailable", message=str(exc), status_code=503)


@router.delete("/notes/{item_id}")
@router.delete("/maybes/items/{item_id}")
def delete_note(
    item_id: str,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
    gate_chain: GateChain = Depends(get_gate_chain),
):
    require_tenant_membership(auth, context.tenant_id)
    _enforce_gate(gate_chain, context, "maybes_delete")
    try:
        service.delete_item(context, item_id)
        return {"status": "deleted"}
    except MaybesNotFound as exc:
        return error_response(code="maybes.not_found", message=str(exc), status_code=404)
    except RuntimeError as exc:
        return error_response(code="maybes.service_unavailable", message=str(exc), status_code=503)
