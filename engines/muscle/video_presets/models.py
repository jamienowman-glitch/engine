from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from engines.video_timeline.models import Filter, ParameterAutomation


def _uuid() -> str:
    return uuid.uuid4().hex


class FilterPreset(BaseModel):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    filters: List[Filter] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)


class MotionPreset(BaseModel):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    duration_ms: int
    tracks: List[ParameterAutomation] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)
