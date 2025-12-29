from __future__ import annotations
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class FeatureTags(BaseModel):
    bpm: Optional[float] = None
    key_root: Optional[str] = None # e.g. "C", "F#"
    key_scale: Optional[str] = None # "major", "minor"
    brightness: Optional[float] = None # Spectral centroid mean
    noisiness: Optional[float] = None # Zero crossing rate mean
    dynamic_range_db: Optional[float] = None # Peak - RMS ?

class NormaliseRequest(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    
    # Input
    asset_id: Optional[str] = None
    artifact_id: Optional[str] = None
    
    # Params
    target_lufs: float = -14.0
    peak_ceiling_dbfs: float = -1.0
    # For tagging only without normalizing, could assume target_lufs=None? 
    # Or separate request?
    # Plan says "NormaliseRequest ... NormaliseResult". 
    # Tagging might be implicit or separate.
    # We'll allow skipping normalization if target_lufs is 0 or None? 
    # Let's say explicit flag?
    skip_normalization: bool = False
    
    output_format: str = "wav"

class NormaliseResult(BaseModel):
    artifact_id: Optional[str] = None # None if only tagging existing?
    uri: Optional[str] = None
    lufs_measured: Optional[float] = None
    peak_dbfs: Optional[float] = None
    tags: Optional[FeatureTags] = None
    meta: Dict[str, Any] = Field(default_factory=dict)
