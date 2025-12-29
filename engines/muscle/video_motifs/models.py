from __future__ import annotations
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class MotifClip(BaseModel):
    # Abstract representation of a clip in a motif
    relative_start_ms: float
    duration_ms: float
    track_offset: int # relative index (0 = main track)
    role: str # e.g. "main", "b-roll", "overlay"
    filters: List[Any] = Field(default_factory=list)

class Motif(BaseModel):
    id: str
    name: str
    clips: List[MotifClip] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
