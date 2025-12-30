"""Session Memory models."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class SessionTurn(BaseModel):
    """
    A single turn in a conversation session.
    Placeholder data carrier; no semantic interpretation.
    """
    turn_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    role: str = Field(..., description="user | agent | system")
    content: str = Field(..., description="Text content (opaque)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionSnapshot(BaseModel):
    """
    Full history of a session.
    """
    session_id: str
    tenant_id: str
    mode: str
    project_id: str
    turns: List[SessionTurn] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
