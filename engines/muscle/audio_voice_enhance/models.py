from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


VoiceEnhanceMode = Literal["default", "podcast", "vlog", "phone_recording"]


class VoiceEnhanceRequest(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    asset_id: str
    artifact_id: Optional[str] = None
    mode: VoiceEnhanceMode = "default"
    target_speaker_id: Optional[str] = None
    aggressiveness: float = 0.5
    preserve_ambience: bool = True


class VoiceEnhanceResult(BaseModel):
    artifact_id: str
    uri: str
    meta: Dict[str, Any] = Field(default_factory=dict)
