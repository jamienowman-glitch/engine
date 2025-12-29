from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MessageRecord(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=_now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionMemory(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    tenant_id: str
    mode: str
    project_id: str
    user_id: str
    session_id: str
    messages: List[MessageRecord] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ttl_hint: Optional[int] = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class Blackboard(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    tenant_id: str
    mode: str
    project_id: str
    surface: Optional[str] = None
    scope: str = "session"
    key: str
    data: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
