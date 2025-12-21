from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class SamplePackRequest(BaseModel):
    tenant_id: str
    env: str
    
    input_asset_ids: List[str] # Raw field recordings
    name: str # Pack Name
    
    fx_preset_id: Optional[str] = None # Apply this preset to all samples (or per type logic?)
    # Usually we want clean + fx versions? Or just one. 
    # For V1: Single pass. If preset given, apply it.
    
    normalise_target_lufs: float = -14.0
    
class SamplePackItem(BaseModel):
    artifact_id: str
    path: str # e.g. "Drums/Kicks/kick_01.wav"
    role: str
    meta: Dict[str, Any] = Field(default_factory=dict)

class SamplePackResult(BaseModel):
    pack_artifact_id: str
    pack_uri: Optional[str]
    items: List[SamplePackItem]
    meta: Dict[str, Any] = Field(default_factory=dict)
