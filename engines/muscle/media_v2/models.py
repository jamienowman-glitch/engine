from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, root_validator

MediaKind = Literal["video", "audio", "image", "other"]
ArtifactKind = Literal[
    "audio_segment",
    "audio_clean",
    "frame",
    "stem",
    "mask",
    "render",
    "render_segment",
    "render_snippet",
    "asr_transcript",
    "bars",
    "beat_features",
    "visual_meta",
    "audio_semantic_timeline",
    "audio_voice_enhanced",
    "render_360",
    "video_region_summary",
    "audio_hit",
    "audio_loop",
    "audio_phrase",
    "audio_sample_fx",
    "audio_sample_norm",
    "audio_render",
    "audio_resampled",
    "audio_bus_stem",
    "sample_pack",
    "audio_groove_profile",
    "video_shot_list",
    "audio_macro",
    "audio_stem_drum",
    "audio_stem_bass",
    "audio_stem_vocal",
    "audio_stem_other",
    "audio_mix_snapshot",
    "video_automation_curve",
    "video_proxy",
    "video_proxy_360p",
    "video_proxy_720p",
    "video_stabilise_transform",
    "image_render",
    "vector_scene",
    "text_render",
    "image_composition",
    "cad_model",
    "cad_semantics",
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

    @root_validator(skip_on_failure=True)
    def _ensure_tenant_env_and_meta(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        tenant_id = values.get("tenant_id")
        env = values.get("env")
        meta = dict(values.get("meta") or {})
        if not tenant_id or not env:
            raise ValueError("DerivedArtifact requires tenant_id and env")
        kind = values.get("kind")
        meta_updates = _REQUIRED_META.get(kind)
        if meta_updates:
            for key, default in meta_updates.items():
                if key not in meta:
                    meta[key] = default(kind)
        values["meta"] = meta
        return values

_REQUIRED_META: Dict[str, Dict[str, Any]] = {
    "video_region_summary": {
        "backend_version": lambda kind: f"{kind}_unknown",
        "model_used": lambda kind: f"{kind}_unknown",
        "cache_key": lambda kind: f"{kind}_auto_cache",
        "duration_ms": lambda kind: 0,
    },
    "visual_meta": {
        "backend_version": lambda kind: f"{kind}_unknown",
        "model_used": lambda kind: f"{kind}_unknown",
        "cache_key": lambda kind: f"{kind}_auto_cache",
        "duration_ms": lambda kind: 0,
        "frame_sample_interval_ms": lambda kind: 0,
    },
    "asr_transcript": {
        "backend_version": lambda kind: f"{kind}_unknown",
        "model_used": lambda kind: f"{kind}_unknown",
        "cache_key": lambda kind: f"{kind}_auto_cache",
        "duration_ms": lambda kind: 0,
    },
}

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
