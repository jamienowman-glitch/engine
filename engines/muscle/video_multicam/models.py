from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


MultiCamRole = Literal["primary", "secondary", "wide", "detail", "alt"]


class MultiCamTrackSpec(BaseModel):
    asset_id: str
    role: MultiCamRole = "primary"
    label: Optional[str] = None
    offset_ms: Optional[int] = None  # Offset relative to base_asset (positive means this track starts later)
    meta: Dict[str, Any] = Field(default_factory=dict)


class MultiCamSession(BaseModel):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    project_id: Optional[str] = None  # Link to video_timeline project
    name: str
    tracks: List[MultiCamTrackSpec] = Field(default_factory=list)
    base_asset_id: Optional[str] = None  # The reference asset for alignment (offset 0)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    meta: Dict[str, Any] = Field(default_factory=dict)


class CreateMultiCamSessionRequest(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    name: str
    tracks: List[MultiCamTrackSpec]
    base_asset_id: Optional[str] = None


class MultiCamAlignRequest(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    session_id: str
    alignment_method: Literal["waveform_cross_correlation", "stub"] = "waveform_cross_correlation"
    max_search_ms: int = 5000


class MultiCamAlignResult(BaseModel):
    session_id: str
    offsets_ms: Dict[str, int]
    meta: Dict[str, Any] = Field(default_factory=dict)


class MultiCamBuildSequenceRequest(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    session_id: str
    project_id: Optional[str] = None  # If None, create new project


class MultiCamBuildSequenceResult(BaseModel):
    session_id: str
    project_id: str
    sequence_id: str
    track_ids: Dict[str, str]  # asset_id -> track_id


class MultiCamAutoCutRequest(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    session_id: str
    project_id: Optional[str] = None
    base_sequence_id: Optional[str] = None
    min_shot_duration_ms: int = 1500
    max_shot_duration_ms: int = 6000
    prefer_primary_ratio: float = 0.6


class MultiCamAutoCutResult(BaseModel):
    session_id: str
    project_id: str
    sequence_id: str
    meta: Dict[str, Any] = Field(default_factory=dict)
