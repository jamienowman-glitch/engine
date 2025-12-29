from __future__ import annotations
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class ResampleRequest(BaseModel):
    tenant_id: str
    env: str
    
    artifact_id: str
    
    # Resample Params
    target_bpm: Optional[float] = None
    input_bpm: Optional[float] = None # Optional override if metadata missing
    
    pitch_semitones: float = 0.0 # +/- semitones
    quality_preset: Optional[str] = "high" # high, fast
    
    preserve_formants: bool = False # Use formant preservation if possible?

class ResampleResult(BaseModel):
    artifact_id: str
    uri: str
    duration_ms: float
    meta: Dict[str, Any] = Field(default_factory=dict)
