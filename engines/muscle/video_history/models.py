from __future__ import annotations
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import time

class Snapshot(BaseModel):
    id: str
    sequence_id: str
    timestamp: float = Field(default_factory=time.time)
    data: Dict[str, Any] # Serialized sequence/tracks/clips
    description: Optional[str] = None

class Change(BaseModel):
    type: str # ADD, REMOVE, UPDATE
    target_type: str # CLIP, TRACK
    target_id: str
    diff: Optional[Dict[str, Any]] = None

class Diff(BaseModel):
    snapshot_a_id: str
    snapshot_b_id: str
    changes: List[Change]
