from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from engines.video_timeline.models import ParameterAutomation

class FocusRequest(BaseModel):
    clip_id: str
    asset_id: str
    tenant_id: Optional[str] = None
    env: Optional[str] = None
    audio_artifact_id: Optional[str] = None
    visual_artifact_id: Optional[str] = None
    target_aspect_ratio: str = "9:16" 

class FocusResult(BaseModel):
    clip_id: str
    automation_x: ParameterAutomation
    automation_y: ParameterAutomation
    meta: Dict[str, Any] = Field(default_factory=dict)
