from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

OriginSnippetTargetKind = Literal["audio_hit", "audio_loop", "audio_phrase"]
OriginSnippetMode = Literal["timeline_only", "render_clips"]


class OriginSnippetRequestItem(BaseModel):
    audio_artifact_id: str
    padding_ms: float = 250
    max_duration_ms: Optional[float] = None


class OriginSnippetBatchRequest(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    items: List[OriginSnippetRequestItem] = Field(default_factory=list)
    mode: OriginSnippetMode = "timeline_only"
    attach_to_project_id: Optional[str] = None
    render_profile: Optional[str] = None


class OriginSnippet(BaseModel):
    audio_artifact_id: str
    source_asset_id: str
    source_start_ms: float
    source_end_ms: float
    video_clip_id: Optional[str] = None
    video_artifact_id: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class OriginSnippetBatchResult(BaseModel):
    snippets: List[OriginSnippet] = Field(default_factory=list)
    project_id: Optional[str] = None
    sequence_id: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)
