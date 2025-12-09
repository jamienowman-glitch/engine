"""FastAPI routes for Maybes scratchpad notes."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from engines.maybes.schemas import MaybesFilters, MaybesNote
from engines.maybes.service import (
    CanvasLayoutUpdate,
    MaybesForbidden,
    MaybesNotFound,
    MaybesService,
)
from engines.maybes.repository import get_maybes_repository

router = APIRouter(prefix="/api/maybes")
service = MaybesService(repository=get_maybes_repository())


class MaybesCreateRequest(BaseModel):
    tenant_id: str = Field(..., pattern=r"^t_[a-z0-9_-]+$")
    user_id: str
    body: str
    title: Optional[str] = None
    colour_token: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    origin_ref: dict = Field(default_factory=dict)
    episode_id: Optional[str] = None
    layout_x: float = 0.0
    layout_y: float = 0.0
    layout_scale: float = 1.0


class MaybesUpdateRequest(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    colour_token: Optional[str] = None
    tags: Optional[List[str]] = None
    origin_ref: Optional[dict] = None
    is_pinned: Optional[bool] = None
    is_archived: Optional[bool] = None
    layout_x: Optional[float] = None
    layout_y: Optional[float] = None
    layout_scale: Optional[float] = None
    episode_id: Optional[str] = None
    nexus_doc_id: Optional[str] = None


class CanvasLayoutEntry(BaseModel):
    maybes_id: str
    layout_x: float
    layout_y: float
    layout_scale: float


class CanvasLayoutRequest(BaseModel):
    tenant_id: str = Field(..., pattern=r"^t_[a-z0-9_-]+$")
    user_id: str
    layouts: List[CanvasLayoutEntry]


@router.get("")
def list_maybes(
    tenant_id: str = Query(..., pattern=r"^t_[a-z0-9_-]+$"),
    user_id: str = Query(...),
    tags: Optional[str] = None,
    search: Optional[str] = None,
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None,
    origin_surface: Optional[str] = None,
    origin_app: Optional[str] = None,
    origin_thread_id: Optional[str] = None,
    origin_message_id: Optional[str] = None,
    include_archived: bool = False,
) -> dict:
    origin_ref = {
        k: v
        for k, v in {
            "surface": origin_surface,
            "app": origin_app,
            "thread_id": origin_thread_id,
            "message_id": origin_message_id,
        }.items()
        if v is not None
    }
    filters = MaybesFilters(
        tags=[t for t in (tags.split(",") if tags else []) if t],
        search=search,
        created_after=created_after,
        created_before=created_before,
        origin_ref=origin_ref,
        include_archived=include_archived,
    )
    notes = service.list_notes(tenant_id=tenant_id, user_id=user_id, filters=filters)
    return {"items": [n.model_dump() for n in notes]}


@router.post("", response_model=MaybesNote)
def create_maybes(req: MaybesCreateRequest) -> MaybesNote:
    return service.create_note(
        tenant_id=req.tenant_id,
        user_id=req.user_id,
        body=req.body,
        title=req.title,
        colour_token=req.colour_token,
        tags=req.tags,
        origin_ref=req.origin_ref,
        episode_id=req.episode_id,
        layout_x=req.layout_x,
        layout_y=req.layout_y,
        layout_scale=req.layout_scale,
    )


@router.patch("/{maybes_id}", response_model=MaybesNote)
def update_maybes(maybes_id: str, req: MaybesUpdateRequest, tenant_id: str, user_id: str) -> MaybesNote:
    try:
        return service.update_note(maybes_id, tenant_id, user_id, req.model_dump(exclude_none=True))
    except MaybesNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except MaybesForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.delete("/{maybes_id}")
def archive_maybes(maybes_id: str, tenant_id: str, user_id: str) -> dict:
    try:
        note = service.archive_note(maybes_id, tenant_id, user_id)
        return {"status": "archived", "maybes_id": note.maybes_id}
    except MaybesNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except MaybesForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.get("/canvas-layout")
def get_canvas_layout(tenant_id: str, user_id: str) -> dict:
    layouts = service.get_canvas_layout(tenant_id=tenant_id, user_id=user_id)
    return {"layouts": layouts}


@router.post("/canvas-layout")
def save_canvas_layout(req: CanvasLayoutRequest) -> dict:
    updates = [
        CanvasLayoutUpdate(
            maybes_id=entry.maybes_id,
            layout_x=entry.layout_x,
            layout_y=entry.layout_y,
            layout_scale=entry.layout_scale,
        )
        for entry in req.layouts
    ]
    try:
        layout = service.save_canvas_layout(
            tenant_id=req.tenant_id,
            user_id=req.user_id,
            layouts=updates,
        )
        return {"layouts": layout}
    except MaybesNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except MaybesForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc))
