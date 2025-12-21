from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AudioBaseRequest(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    asset_id: str
    artifact_id: Optional[str] = None


class PreprocessRequest(AudioBaseRequest):
    options: Dict[str, Any] = Field(default_factory=dict)


class SegmentRequest(AudioBaseRequest):
    segment_seconds: int = 90
    overlap_seconds: int = 0


class BeatFeaturesRequest(AudioBaseRequest):
    artifact_ids: List[str] = Field(default_factory=list)


class AsrRequest(AudioBaseRequest):
    artifact_ids: List[str] = Field(default_factory=list)
    model_name: str = "medium"
    device: str = "cpu"
    compute_type: str = "int8"


class AlignRequest(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    asr_artifact_ids: List[str]
    beat_meta: Dict[str, Any] = Field(default_factory=dict)


class VoiceEnhanceRequest(AudioBaseRequest):
    mode: str = "default"
    target_speaker_id: Optional[str] = None
    aggressiveness: float = 0.5
    preserve_ambience: bool = True


class ArtifactRef(BaseModel):
    artifact_id: str
    uri: str
    meta: Dict[str, Any] = Field(default_factory=dict)
