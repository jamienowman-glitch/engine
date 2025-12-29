from __future__ import annotations

import uuid
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field



from .profiles import RenderProfile


class RenderRequest(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    project_id: str
    start_ms: Optional[float] = None
    end_ms: Optional[float] = None
    overlap_ms: float = 0.0
    segment_index: Optional[int] = None
    render_profile: RenderProfile = "social_1080p_h264"
    output_path: Optional[str] = None
    storage_target: Literal["local", "gcs"] = "local"
    audio_mixdown: Literal["stereo", "mono"] = "stereo"
    watermark: Optional[Dict[str, Any]] = None
    dry_run: bool = False
    normalize_audio: bool = False
    target_loudness_lufs: Optional[float] = None
    ducking: Optional[Dict[str, Any]] = None
    use_voice_enhanced_audio: bool = False
    voice_enhance_mode: Optional[str] = None
    voice_enhance_if_available_only: bool = True
    use_proxies: bool = False
    burn_in_captions: Optional[Dict[str, Any]] = None  # e.g. {"artifact_id": "...", "style": "default"}


class PlanStep(BaseModel):
    description: str
    ffmpeg_args: List[str] = Field(default_factory=list)


class RenderPlan(BaseModel):
    inputs: List[str] = Field(default_factory=list)
    input_meta: List[Dict[str, Any]] = Field(default_factory=list)
    steps: List[PlanStep] = Field(default_factory=list)
    output_path: str
    profile: RenderProfile
    filters: List[str] = Field(default_factory=list)
    audio_filters: List[str] = Field(default_factory=list)
    start_ms: Optional[float] = None
    end_ms: Optional[float] = None
    overlap_ms: float = 0.0
    meta: Dict[str, Any] = Field(default_factory=dict)


class RenderResult(BaseModel):
    asset_id: str
    artifact_id: str
    uri: str
    render_profile: RenderProfile
    plan_preview: RenderPlan


class RenderSegment(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    project_id: str
    sequence_id: str
    segment_index: int
    start_ms: float
    end_ms: float
    overlap_ms: float
    profile: RenderProfile
    cache_key: Optional[str] = None


class ChunkPlanRequest(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    project_id: str
    render_profile: RenderProfile = "social_1080p_h264"
    segment_duration_ms: int = 15000
    overlap_ms: int = 750


class SegmentJobsRequest(BaseModel):
    render_request: RenderRequest
    segments: List[RenderSegment]


class StitchRequest(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    project_id: str
    render_profile: RenderProfile = "social_1080p_h264"
    segment_job_ids: List[str]
    output_path: Optional[str] = None
    storage_target: Literal["local", "gcs"] = "local"
    normalize_audio: bool = False
    target_loudness_lufs: Optional[float] = None
