from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class KillSwitch(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    tenant_id: str
    env: str
    disable_providers: List[str] = Field(default_factory=list)
    disable_autonomy: bool = False
    disabled_actions: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class KillSwitchUpdate(BaseModel):
    disable_providers: Optional[List[str]] = None
    disable_autonomy: Optional[bool] = None
    disabled_actions: Optional[List[str]] = None
