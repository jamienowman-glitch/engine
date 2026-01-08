from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, List
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Firearm(BaseModel):
    """
    A specific capability/license definition.
    Example: 'firearm.database_write'
    """
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str # e.g. "Database Write Access"
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)


class FirearmGrant(BaseModel):
    """
    Assignment of a Firearm to an actor within a scope.
    """
    id: str = Field(default_factory=lambda: uuid4().hex)
    firearm_id: str
    granted_to_agent_id: Optional[str] = None
    granted_to_user_id: Optional[str] = None
    tenant_id: str
    project_id: Optional[str] = None # Optional scope
    surface_id: Optional[str] = None # Optional scope
    granted_by: str = "system"
    granted_at: datetime = Field(default_factory=_now)
    expires_at: Optional[datetime] = None
    revoked: bool = False


class FirearmBinding(BaseModel):
    """
    Link between an Action (Tool/Command) and a Firearm.
    Example: Action 'tool.postgres.execute_query' requires 'firearm.database_write'
    """
    action_name: str # The action identifier (e.g. 'tool.postgres.execute_query')
    firearm_id: str
    strategy_lock_required: bool = True # Hard rule: if firearm bound, lock required.
    created_at: datetime = Field(default_factory=_now)


class FirearmDecision(BaseModel):
    allowed: bool
    reason: Optional[str] = None
    firearm_id: Optional[str] = None
    required_license_types: List[str] = Field(default_factory=list)
    strategy_lock_required: bool = False
