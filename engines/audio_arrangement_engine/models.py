from __future__ import annotations
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from engines.audio_timeline.models import AudioSequence

class ArrangementSection(BaseModel):
    name: str # e.g. "Intro"
    bars: int
    active_roles: List[str] # ["drums", "bass"]

class ArrangementTemplate(BaseModel):
    id: str
    sections: List[ArrangementSection]

class ArrangementRequest(BaseModel):
    tenant_id: str
    env: str
    template_id: str
    bpm: float
    
    # Input patterns: Role -> List of Clip dicts (relative start_ms)
    # Similar to P5 but more formal
    pattern_clips_by_role: Dict[str, List[Dict[str, Any]]] 
    
    # Optional overrides
    seed: Optional[int] = None

class ArrangementResult(BaseModel):
    sequence: AudioSequence
    meta: Dict[str, Any] = Field(default_factory=dict)
