from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def _uuid() -> str:
    return uuid.uuid4().hex


class HitDetectRequest(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    asset_id: Optional[str] = None
    artifact_id: Optional[str] = None
    
    # Tuning params
    pre_roll_ms: int = 10
    post_roll_ms: int = 200
    min_peak_db: float = -40.0
    min_interval_ms: int = 50
    max_duration_ms: int = 2000 # Limit hit length (if slicing hits) or used for auto-slicing window
    
    meta: Dict[str, Any] = Field(default_factory=dict)


class HitEvent(BaseModel):
    time_ms: float
    peak_db: float
    energy: Optional[float] = None
    duration_ms: Optional[float] = None # Estimated length of the hit sound
    source_start_ms: float # The cut start
    source_end_ms: float # The cut end


class HitDetectResult(BaseModel):
    events: List[HitEvent] = Field(default_factory=list)
    artifact_ids: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)
