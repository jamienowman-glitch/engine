from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class VoicePhraseDetectRequest(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    asset_id: Optional[str] = None
    artifact_id: Optional[str] = None # Or "transcript_artifact_id"? 
    # Usually we pass asset_id and let service find Transcript
    
    # Params
    max_gap_ms: int = 500 # Merge words if gap <= 500ms
    min_phrase_len_ms: int = 200 # Ignore tiny blips
    
    meta: Dict[str, Any] = Field(default_factory=dict)


class VoicePhrase(BaseModel):
    start_ms: float
    end_ms: float
    transcript: str
    confidence: float
    source_start_ms: float
    source_end_ms: float


class VoicePhraseDetectResult(BaseModel):
    phrases: List[VoicePhrase] = Field(default_factory=list)
    artifact_ids: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)
