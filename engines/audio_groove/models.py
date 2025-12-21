from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class GrooveProfile(BaseModel):
    bpm: float
    subdivision: int = 16 # Steps per bar (16 = 16th notes)
    offsets: List[float] # Offsets in ms for each step in the bar (usually 16)
    confidence: float = 1.0

class GrooveExtractRequest(BaseModel):
    tenant_id: str
    env: str
    
    artifact_id: str
    subdivision: int = 16
    
    # If missing BPM in metadata, allow override?
    bpm_hint: Optional[float] = None

class GrooveExtractResult(BaseModel):
    artifact_id: str
    uri: str
    profile: GrooveProfile
    meta: Dict[str, Any] = Field(default_factory=dict)
