from __future__ import annotations
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class SeparationRequest(BaseModel):
    tenant_id: str
    env: str
    artifact_id: str
    model_name: str = "htdemucs" # standard demucs model
    two_stems: Optional[str] = None # e.g. "vocals" to split vocals/other only

class SeparationResult(BaseModel):
    source_artifact_id: str
    # Map role -> artifact_id
    # Roles: drums, bass, vocals, other
    stems: Dict[str, str]
    meta: Dict[str, Any] = Field(default_factory=dict)
