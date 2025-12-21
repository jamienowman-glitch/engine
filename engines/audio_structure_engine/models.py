from __future__ import annotations
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from engines.audio_timeline.models import AudioSequence

class StructureSection(BaseModel):
    name: str # e.g. "Intro"
    bars: int
    active_roles: List[str] # ["kick", "snare", "hat"]

class StructureTemplate(BaseModel):
    id: str
    name: str
    sections: List[StructureSection]

class ArrangementRequest(BaseModel):
    tenant_id: str
    env: str
    template_id: str
    
    # Map role -> Artifact ID of the sample to use (or PatternResult logic?)
    # Actually, P5 says "arrange patterns". 
    # A pattern is a set of clips. 
    # To facilitate reuse, we might need pre-generated patterns per role?
    # Or we pass the pattern parameters and generate inside?
    # Simpler: Pass a list of "Pattern Clips" for one bar. 
    # The structure engine repeats them.
    # So input: dict[role, List[AudioClip_Dict]]
    pattern_clips_by_role: Dict[str, List[Dict[str, Any]]] 
    
    bpm: float = 120.0

class ArrangementResult(BaseModel):
    sequence: AudioSequence
    meta: Dict[str, Any] = Field(default_factory=dict)
