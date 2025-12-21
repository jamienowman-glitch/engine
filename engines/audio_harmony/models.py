from __future__ import annotations
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

ScaleType = Literal["major", "minor", "unknown"]

class KeyEstimate(BaseModel):
    root: str # C, C#, D...
    scale: ScaleType
    confidence: float

class HarmonyRequest(BaseModel):
    tenant_id: str
    env: str
    artifact_id: str
    target_key_root: str
    target_scale: ScaleType = "major"

class HarmonyResult(BaseModel):
    artifact_id: str
    uri: str
    meta: Dict[str, Any] = Field(default_factory=dict)
