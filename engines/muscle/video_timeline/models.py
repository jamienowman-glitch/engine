from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


def _uuid() -> str:
    return uuid.uuid4().hex


class Timestamped(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VideoProject(Timestamped):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    render_profile: Optional[str] = None
    sequence_ids: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)


class Sequence(Timestamped):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    project_id: str
    name: str
    duration_ms: Optional[float] = None
    timebase_fps: Optional[float] = None
    track_ids: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)


class Track(Timestamped):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    sequence_id: str
    kind: Literal["video", "audio"]
    order: int = 0
    muted: bool = False
    hidden: bool = False
    audio_role: Optional[Literal["generic", "dialogue", "music", "fx", "ambience"]] = "generic"
    video_role: Optional[Literal["main", "b-roll", "overlay", "generic"]] = "generic"
    meta: Dict[str, Any] = Field(default_factory=dict)


class Clip(Timestamped):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    track_id: str
    asset_id: str
    artifact_id: Optional[str] = None
    mask_artifact_id: Optional[str] = None
    in_ms: float
    out_ms: float
    start_ms_on_timeline: float
    speed: float = 1.0
    volume_db: float = 0.0
    opacity: float = 1.0
    blend_mode: Optional[Literal["normal", "add", "screen", "multiply", "overlay"]] = "normal"
    scale_mode: Optional[str] = None  # fit|fill|custom
    position: Optional[dict] = None  # {"x":..., "y":...}
    crop: Optional[dict] = None  # {"x":..., "y":..., "w":..., "h":...}
    stabilise: bool = False
    optical_flow: bool = False
    alignment_applied: bool = False
    meta: Dict[str, Any] = Field(default_factory=dict)


class Transition(Timestamped):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    sequence_id: str
    type: Literal[
        "crossfade",
        "dip_to_black",
        "dip_to_white",
        "wipe_left",
        "wipe_right",
        "push_left",
        "push_right",
        "none",
    ]
    duration_ms: float
    from_clip_id: str
    to_clip_id: str
    meta: Dict[str, Any] = Field(default_factory=dict)


class Filter(BaseModel):
    type: str
    params: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    mask_artifact_id: Optional[str] = None


class FilterStack(Timestamped):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    target_type: Literal["clip", "track", "sequence"]
    target_id: str
    filters: List[Filter] = Field(default_factory=list)


class ProjectResponse(BaseModel):
    project: VideoProject
    sequences: List[Sequence] = Field(default_factory=list)


class Keyframe(BaseModel):
    time_ms: int
    value: float
    interpolation: Literal["step", "linear", "ease_in", "ease_out", "ease_in_out"] = "linear"


class ParameterAutomation(Timestamped):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    target_type: Literal["clip", "track", "sequence"]
    target_id: str
    property: Literal["position_x", "position_y", "scale", "opacity", "volume_db", "crop_x", "crop_y"]
    keyframes: List[Keyframe] = Field(default_factory=list)

# Valid filter types:
# "color_grade": {brightness, contrast, saturation, hue}
# "teeth_whiten": {intensity}
# "skin_smooth": {intensity}
# "selective_color" (Phase 6)
