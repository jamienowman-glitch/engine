from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LoopDetectRequest(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    asset_id: Optional[str] = None
    artifact_id: Optional[str] = None
    
    # Params
    target_bars: List[int] = Field(default=[1, 2, 4])
    bpm_hint: Optional[float] = None
    min_confidence: float = 0.5
    
    meta: Dict[str, Any] = Field(default_factory=dict)


class LoopEvent(BaseModel):
    start_ms: float
    end_ms: float
    loop_bars: int
    bpm: float
    confidence: float
    source_start_ms: float
    source_end_ms: float


class LoopDetectResult(BaseModel):
    loops: List[LoopEvent] = Field(default_factory=list)
    artifact_ids: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)
