from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

AudioEventKind = Literal["speech", "music", "silence", "other"]


class AudioEvent(BaseModel):
    kind: AudioEventKind
    start_ms: int
    end_ms: int
    speaker_id: Optional[str] = None
    loudness_lufs: Optional[float] = None
    confidence: Optional[float] = None
    transcription: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class BeatEvent(BaseModel):
    time_ms: int
    bar_index: Optional[int] = None
    beat_index: Optional[int] = None
    subdivision: Optional[int] = None


class AudioSemanticTimelineSummary(BaseModel):
    asset_id: str
    artifact_id: Optional[str] = None
    duration_ms: Optional[int] = None
    events: List[AudioEvent] = Field(default_factory=list)
    beats: List[BeatEvent] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)


class AudioSemanticAnalyzeRequest(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    asset_id: str
    artifact_id: Optional[str] = None
    include_beats: bool = True
    include_speech_music: bool = True
    min_silence_ms: int = 300
    loudness_window_ms: int = 1000


class AudioSemanticAnalyzeResult(BaseModel):
    audio_semantic_artifact_id: str
    uri: str
    meta: Dict[str, Any] = Field(default_factory=dict)


class AudioSemanticTimelineGetResponse(BaseModel):
    artifact_id: str
    uri: str
    summary: AudioSemanticTimelineSummary
    artifact_meta: Dict[str, Any] = Field(default_factory=dict)
