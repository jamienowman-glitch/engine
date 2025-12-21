from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field
from engines.video_timeline.models import ParameterAutomation


class SubjectDetection(BaseModel):
    track_id: Optional[str] = None
    label: str
    confidence: float
    bbox_x: float
    bbox_y: float
    bbox_width: float
    bbox_height: float


class VisualMetaFrame(BaseModel):
    timestamp_ms: int
    subjects: List[SubjectDetection] = Field(default_factory=list)
    primary_subject_center_x: Optional[float] = None
    primary_subject_center_y: Optional[float] = None
    shot_boundary: bool = False


class VisualMetaSummary(BaseModel):
    asset_id: str
    artifact_id: Optional[str] = None
    frames: List[VisualMetaFrame]
    duration_ms: Optional[float] = None
    frame_sample_interval_ms: Optional[int] = None


class VisualMetaAnalyzeRequest(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    asset_id: str
    artifact_id: Optional[str] = None
    sample_interval_ms: int = 500
    include_labels: Optional[List[str]] = None
    detect_shot_boundaries: bool = True


class VisualMetaAnalyzeResult(BaseModel):
    visual_meta_artifact_id: str
    uri: str
    meta: Dict[str, Any] = Field(default_factory=dict)


class VisualMetaGetResponse(BaseModel):
    artifact_id: str
    uri: str
    summary: VisualMetaSummary
    artifact_meta: Dict[str, Any] = Field(default_factory=dict)


class ReframeSuggestionRequest(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    clip_id: str
    target_aspect_ratio: Literal["9:16", "16:9", "4:5", "1:1"]
    framing_style: Literal["center", "rule_of_thirds"] = "center"


class ReframeSuggestion(BaseModel):
    clip_id: str
    automation: List[ParameterAutomation]
    meta: Dict[str, Any] = Field(default_factory=dict)
