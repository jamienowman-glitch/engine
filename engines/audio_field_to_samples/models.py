from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FieldToSamplesRequest(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    asset_id: str
    
    # Flags
    run_hits: bool = True
    run_loops: bool = True
    run_phrases: bool = True
    
    # Tuning params passed down
    hit_params: Dict[str, Any] = Field(default_factory=dict)
    loop_params: Dict[str, Any] = Field(default_factory=dict)
    phrase_params: Dict[str, Any] = Field(default_factory=dict)
    min_quality_score: float = 0.0


class FieldToSamplesResult(BaseModel):
    asset_id: str
    hit_artifact_ids: List[str] = Field(default_factory=list)
    loop_artifact_ids: List[str] = Field(default_factory=list)
    phrase_artifact_ids: List[str] = Field(default_factory=list)
    
    summary_meta: Dict[str, Any] = Field(default_factory=dict)
