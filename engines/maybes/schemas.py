"""Schemas for Notes / Maybes (persistent, user-owned)."""
from __future__ import annotations

from datetime import datetime, timezone

from typing import Any, Dict, List, Optional
from uuid import uuid4
from enum import Enum

from pydantic import BaseModel, Field


class MaybeSourceType(str, Enum):
    user = "user"
    agent = "agent"



def _now() -> datetime:
    return datetime.now(timezone.utc)


class NoteSource(BaseModel):
    created_by: str = Field(default="user", pattern="^(user|agent)$")
    agent_id: Optional[str] = None
    run_id: Optional[str] = None


class NoteTimestamps(BaseModel):
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class MaybeItem(BaseModel):
    note_id: str = Field(default_factory=lambda: uuid4().hex)
    tenant_id: str = Field(..., pattern=r"^t_[a-z0-9_-]+$")
    mode: str
    env: Optional[str] = None
    project_id: Optional[str] = None
    surface_id: str
    user_id: str
    title: str
    content: Any
    tags: List[str] = Field(default_factory=list)
    source: NoteSource = Field(default_factory=NoteSource)
    timestamps: NoteTimestamps = Field(default_factory=NoteTimestamps)
    version: int = 1
    deleted: bool = False


class MaybeCreate(BaseModel):
    title: str
    content: Any
    tags: List[str] = Field(default_factory=list)
    surface_id: Optional[str] = None
    project_id: Optional[str] = None
    source: Optional[NoteSource] = None


class MaybeUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[Any] = None
    tags: Optional[List[str]] = None
    source: Optional[NoteSource] = None


class MaybeQuery(BaseModel):
    surface_id: Optional[str] = None
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    tags_any: Optional[List[str]] = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
