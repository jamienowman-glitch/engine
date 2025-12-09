"""Schemas for Maybes scratchpad notes."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MaybesNote(BaseModel):
    maybes_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = Field(..., pattern=r"^t_[a-z0-9_-]+$")
    user_id: str
    body: str
    title: Optional[str] = None
    colour_token: Optional[str] = None
    layout_x: float = 0.0
    layout_y: float = 0.0
    layout_scale: float = 1.0
    tags: List[str] = Field(default_factory=list)
    origin_ref: Dict[str, Any] = Field(default_factory=dict)
    is_pinned: bool = False
    is_archived: bool = False
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    episode_id: Optional[str] = None
    nexus_doc_id: Optional[str] = None
    asset_type: Literal["maybes_note"] = "maybes_note"


class MaybesFilters(BaseModel):
    tags: List[str] = Field(default_factory=list)
    search: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    origin_ref: Dict[str, Any] = Field(default_factory=dict)
    include_archived: bool = False
