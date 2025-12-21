"""FastAPI routes for MAYBES scratchpad."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import get_auth_context, require_tenant_membership
from engines.maybes.schemas import MaybeCreate, MaybeQuery, MaybeUpdate
from engines.maybes.service import MaybesNotFound, MaybesService

router = APIRouter(prefix="/maybes")
service = MaybesService()


def _parse_tags(tags: Optional[str]) -> list[str] | None:
    if tags is None:
        return None
    parts = [t for t in (tags.split(",") if isinstance(tags, str) else []) if t]
    return parts or None


@router.post("/items")
def create_maybe(req: MaybeCreate, context: RequestContext = Depends(get_request_context), auth=Depends(get_auth_context)):
    require_tenant_membership(auth, context.tenant_id)
    try:
        return service.create_item(req, context)
    except MaybesNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/items")
def list_maybes(
    space: Optional[str] = None,
    user_id: Optional[str] = None,
    tags_any: Optional[str] = None,
    search_text: Optional[str] = None,
    pinned_only: bool = False,
    archived: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    query = MaybeQuery(
        tenant_id=context.tenant_id,
        env=context.env,
        space=space,
        user_id=user_id or context.user_id,
        tags_any=_parse_tags(tags_any),
        search_text=search_text,
        pinned_only=pinned_only,
        archived=archived,
        limit=limit,
        offset=offset,
    )
    items = service.list_items(query)
    return {"items": items}


@router.get("/items/{item_id}")
def get_maybe(
    item_id: str,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    try:
        return service.get_item(context, item_id)
    except MaybesNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/items/{item_id}")
def update_maybe(
    item_id: str,
    req: MaybeUpdate,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    try:
        return {"item": service.update_item(context, item_id, req)}
    except MaybesNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/items/{item_id}")
def delete_maybe(
    item_id: str,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    try:
        service.delete_item(context, item_id)
        return {"status": "deleted"}
    except MaybesNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
