from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class PerformanceEvent(BaseModel):
    time_ms: float
    velocity: float # 0.0 to 1.0 (or 127 based)
    duration_ms: float = 100.0
    pitch: Optional[int] = None # For melody

class CaptureRequest(BaseModel):
    tenant_id: str
    env: str
    
    source_artifact_id: str
    target_bpm: float
    grid_subdivision: int = 16 # 1/16th notes
    
    groove_profile_id: Optional[str] = None
    
    # Blend amount: 0.0 = Fully Quantized (Rigid). 1.0 = Fully Human (Original).
    # Default 0.0 (Snap to grid).
    humanise_blend: float = 0.0
    
    seed: Optional[int] = None

class CaptureResult(BaseModel):
    source_artifact_id: str
    events: List[PerformanceEvent]
    meta: Dict[str, Any] = Field(default_factory=dict)
