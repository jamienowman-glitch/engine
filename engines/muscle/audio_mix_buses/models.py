from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field

class BusConfig(BaseModel):
    id: str
    name: str # Display name
    roles: List[str] # List of roles mapped to this bus e.g. ["kick", "snare"]
    gain_db: float = 0.0
    fx_preset_id: Optional[str] = None # P1 preset ID to apply to bus?

class MixGraph(BaseModel):
    id: str
    name: str
    buses: List[BusConfig]
    master_gain_db: float = 0.0
    master_fx_preset_id: Optional[str] = None
