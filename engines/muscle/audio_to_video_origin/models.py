from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from engines.audio_timeline.models import AudioSequence

class OriginMap(BaseModel):
    source_asset_id: str
    source_start_ms: float
    source_end_ms: float

class VideoShot(BaseModel):
    # Source info (from original video)
    source_asset_id: str
    source_start_ms: float
    source_end_ms: float
    
    # Target info (on the timeline)
    target_start_ms: float
    target_duration_ms: float
    
    meta: Dict[str, Any] = Field(default_factory=dict)

class ShotListRequest(BaseModel):
    tenant_id: str
    env: str
    sequence: AudioSequence

class ShotListResult(BaseModel):
    shots: List[VideoShot]
    meta: Dict[str, Any] = Field(default_factory=dict)
