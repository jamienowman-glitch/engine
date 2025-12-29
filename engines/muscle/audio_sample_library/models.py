from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

SampleType = Literal["audio_hit", "audio_loop", "audio_phrase"]

class SampleDescriptor(BaseModel):
    artifact_id: str
    asset_id: str
    kind: SampleType
    uri: str
    source_start_ms: Optional[float] = None
    source_end_ms: Optional[float] = None
    
    # Flattened important meta for easy consumption
    bpm: Optional[float] = None
    loop_bars: Optional[int] = None
    peak_db: Optional[float] = None
    quality_score: Optional[float] = None
    # P2: Normalized Features
    key_root: Optional[str] = None
    brightness: Optional[float] = None
    noisiness: Optional[float] = None
    features: Dict[str, Any] = Field(default_factory=dict)
    role: Optional[str] = None
    
    meta: Dict[str, Any] = Field(default_factory=dict)
    
class SampleLibraryQuery(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    
    # Filters
    parent_asset_id: Optional[str] = None
    kind: Optional[SampleType] = None
    kinds: Optional[List[SampleType]] = None
    
    min_bpm: Optional[float] = None
    max_bpm: Optional[float] = None
    loop_bars: Optional[int] = None
    has_transcript: bool = False
    
    # P2 Filters
    key_root: Optional[str] = None
    min_brightness: Optional[float] = None
    max_brightness: Optional[float] = None
    min_quality_score: Optional[float] = None
    max_quality_score: Optional[float] = None
    role: Optional[str] = None
    
    limit: int = 50
    offset: int = 0

class SampleLibraryResult(BaseModel):
    samples: List[SampleDescriptor] = Field(default_factory=list)
    total_count: Optional[int] = None # If pagination supported deep
    filter_summary: Dict[str, Any] = Field(default_factory=dict)
