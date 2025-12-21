from __future__ import annotations
from typing import List, Optional, Dict, Any, Literal, Tuple
from pydantic import BaseModel, Field, validator
import uuid

def _uuid() -> str:
    return uuid.uuid4().hex


class AutomationPoint(BaseModel):
    time_ms: float
    value: float
    curve: Literal["linear", "hold"] = "linear"

    @validator("time_ms")
    def time_non_negative(cls, v):
        if v < 0:
            raise ValueError("Automation time must be >= 0")
        return v

class AudioClip(BaseModel):
    id: str = Field(default_factory=_uuid)
    asset_id: Optional[str] = None
    artifact_id: Optional[str] = None # Prefer artifacts (processed/normalized)
    
    # Timing (Global Timeline)
    start_ms: float # Where it starts on the timeline
    duration_ms: float # How long it plays
    
    # Source Trimming
    source_offset_ms: float = 0.0 # Start reading source from here
    
    # Clip parameters
    gain_db: float = 0.0
    pan: float = 0.0 # -1.0 to 1.0
    
    fade_in_ms: float = 0.0
    fade_out_ms: float = 0.0
    fade_curve: Literal["tri", "qsin", "hsin", "exp", "log", "par"] = "tri"
    crossfade_in_ms: float = 0.0
    crossfade_out_ms: float = 0.0
    crossfade_curve: Literal["tri", "qsin", "hsin", "exp", "log", "par"] = "tri"

    # Automation map parameter name -> list of automation points (absolute timeline time)
    automation: Dict[str, List[AutomationPoint]] = Field(default_factory=dict)
    
    label: Optional[str] = None

class AudioTrack(BaseModel):
    id: str = Field(default_factory=_uuid)
    name: str = "Audio Track"
    clips: List[AudioClip] = Field(default_factory=list)
    
    # Track controls
    gain_db: float = 0.0
    pan: float = 0.0
    mute: bool = False
    solo: bool = False
    
    order: int = 0
    meta: Dict[str, Any] = Field(default_factory=dict)
    role: str = "music"
    automation: Dict[str, List[AutomationPoint]] = Field(default_factory=dict)

class SectionMarker(BaseModel):
    start_ms: float
    name: str # Intro, Verse, Chorus...
    duration_bars: Optional[float] = None
    
class AudioSequence(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    env: str
    
    bpm: float = 120.0
    duration_ms: float = 0.0 # If 0, auto-calculated from clips
    
    tracks: List[AudioTrack] = Field(default_factory=list)
    markers: List[SectionMarker] = [] # P9 addition
    
    meta: Dict[str, Any] = Field(default_factory=dict)

class AudioProject(BaseModel):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    env: str
    name: str = "New Project"
    sequences: List[AudioSequence] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)
