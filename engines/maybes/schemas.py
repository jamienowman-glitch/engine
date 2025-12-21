"""Schemas for MAYBES scratchpad items."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MaybeSourceType(str, Enum):
    agent = "agent"
    user = "user"
    system = "system"


class MaybeItem(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    tenant_id: str = Field(..., pattern=r"^t_[a-z0-9_-]+$")
    env: str
    space: str
    user_id: Optional[str] = None
    title: str
    body: str
    tags: List[str] = Field(default_factory=list)
    source_type: MaybeSourceType = MaybeSourceType.agent
    source_engine: Optional[str] = None
    source_ref: Optional[Dict[str, Any]] = None
    pinned: bool = False
    archived: bool = False
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class MaybeCreate(BaseModel):
    tenant_id: Optional[str] = None
    env: Optional[str] = None
    space: str
    user_id: Optional[str] = None
    title: str
    body: str
    tags: List[str] = Field(default_factory=list)
    source_type: MaybeSourceType = MaybeSourceType.agent
    source_engine: Optional[str] = None
    source_ref: Optional[Dict[str, Any]] = None
    pinned: bool = False


class MaybeUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    tags: Optional[List[str]] = None
    pinned: Optional[bool] = None
    archived: Optional[bool] = None


class MaybeQuery(BaseModel):
    tenant_id: str = Field(..., pattern=r"^t_[a-z0-9_-]+$")
    env: str
    space: Optional[str] = None
    user_id: Optional[str] = None
    tags_any: Optional[List[str]] = None
    search_text: Optional[str] = None
    pinned_only: bool = False
    archived: Optional[bool] = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
