from __future__ import annotations
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class PatternTrackTemplate(BaseModel):
    role: str # "kick", "snare", "hat", "percs", "fx"
    steps: List[float] # List of velocities (0.0 to 1.0). Length determines grid (16 for 1 bar 16ths).
    
class PatternTemplate(BaseModel):
    id: str
    name: str
    bpm_default: float = 120.0
    time_signature: str = "4/4"
    bars: int = 1
    swing_default: float = 0.0 # Percentage 0-100
    tracks: List[PatternTrackTemplate] = Field(default_factory=list)

class PatternRequest(BaseModel):
    tenant_id: str
    env: str
    
    template_id: str
    sample_map: Dict[str, str] # role -> artifact_id (e.g. {"kick": "art_123"})
    
    bpm: Optional[float] = None # Override
    swing_pct: Optional[float] = None # Override
    groove_profile_id: Optional[str] = None # Apply extracted groove timings
    
    seed: Optional[int] = None # For random variations if implemented

class PatternResult(BaseModel):
    # We return a list of dicts representing clips, or explicit AudioClip models?
    # Ideally standard models, but to avoid strict dependency on audio_timeline in models.py (circular?), 
    # we can define a schematic or import if safe.
    # We'll return a schematic list that can be converted to AudioClips.
    # Or import AudioClip if it's lightweight. 
    # Let's return a list of dicts that match AudioClip inputs.
    clips: List[Dict[str, Any]] = Field(default_factory=list)
    
    meta: Dict[str, Any] = Field(default_factory=dict)
