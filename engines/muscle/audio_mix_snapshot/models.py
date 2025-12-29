from __future__ import annotations
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class TrackState(BaseModel):
    name: str # Assume unique per sequence? or use order/id
    gain_db: float
    pan: float = 0.0
    active: bool = True
    # Simplified effects list
    effects: List[str] = Field(default_factory=list)

class MixSnapshot(BaseModel):
    id: str
    timestamp_ms: float = 0.0
    tracks: Dict[str, TrackState] # name -> state
    complexity_score: int = 0
    meta: Dict[str, Any] = Field(default_factory=dict)

class CaptureRequest(BaseModel):
    tenant_id: str
    env: str
    # Reference to a MixGraph or Sequence by ID?
    # Or pass the object directly?
    # For V1 passing data object or dict representation if small.
    # Let's assume we capture FROM an AudioSequence object passed in request
    # but that's not Pydantic friendly if passed over wire.
    # We'll pass `audio_sequence` dict.
    audio_sequence: Dict[str, Any] 

class DeltaRequest(BaseModel):
    tenant_id: str
    env: str
    snapshot_a_id: str
    snapshot_b_id: str

class MixDelta(BaseModel):
    snapshot_a_id: str
    snapshot_b_id: str
    
    added_tracks: List[str] = []
    removed_tracks: List[str] = []
    changed_tracks: Dict[str, Dict[str, Any]] = {} # name -> {field: (old, new)}
    
    complexity_delta: int = 0
