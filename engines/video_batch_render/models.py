from __future__ import annotations
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field

class RenderProfile(BaseModel):
    width: int
    height: int
    codec: str = "h264"
    bitrate_kbps: int = 5000
    format: str = "mp4" # container
    label: str # e.g. "Landscape 1080p"

class BatchRenderRequest(BaseModel):
    project_id: str
    profiles: List[RenderProfile]

class BatchRenderPlan(BaseModel):
    project_id: str
    plans: Dict[str, Any] # Map of label -> RenderPlan

class BatchRenderResult(BaseModel):
    batch_id: str
    artifacts: Dict[str, str] = Field(default_factory=dict) # label -> artifact_id
    meta: Dict[str, Any] = Field(default_factory=dict)
