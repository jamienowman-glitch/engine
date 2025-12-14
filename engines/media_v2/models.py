from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, validator

MediaKind = Literal["video", "audio", "image", "other"]
ArtifactKind = Literal[
    "audio_segment",
    "audio_clean",
    "frame",
    "stem",
    "mask",
    "render",
    "render_segment",
    "asr_transcript",
    "bars",
    "beat_features",
    "visual_meta",
    "audio_semantic_timeline",
    "audio_voice_enhanced",
    "render_360",
    "video_region_summary",
]


def _uuid() -> str:
    return uuid.uuid4().hex


class MediaAsset(BaseModel):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    kind: MediaKind = "other"
    source_uri: str
    duration_ms: Optional[float] = None
    fps: Optional[float] = None
    audio_channels: Optional[int] = None
    sample_rate: Optional[int] = None

    # 360 Video specific
    is_360: bool = False
    projection: Optional[str] = None  # e.g. "equirectangular"

    # Meta
    codec_info: Optional[str] = None
    size_bytes: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    source_ref: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    meta: Dict[str, Any] = Field(default_factory=dict)


class DerivedArtifact(BaseModel):
    id: str = Field(default_factory=_uuid)
    parent_asset_id: str
    tenant_id: str
    env: str
    kind: ArtifactKind
    uri: str
    start_ms: Optional[float] = None
    end_ms: Optional[float] = None
    track_label: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    meta: Dict[str, Any] = Field(default_factory=dict)

# Backwards compatibility alias for older imports
Artifact = DerivedArtifact


class MediaUploadRequest(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    kind: Optional[MediaKind] = None
    source_uri: str
    source_ref: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)


class ArtifactCreateRequest(BaseModel):
    tenant_id: str
    env: str
    parent_asset_id: str
    kind: ArtifactKind
    uri: str
    start_ms: Optional[float] = None
    end_ms: Optional[float] = None
    track_label: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class MediaAssetResponse(BaseModel):
    asset: MediaAsset
    artifacts: List[DerivedArtifact] = Field(default_factory=list)
