from __future__ import annotations

from pathlib import Path
from typing import List, Literal, Dict, Any

from pydantic import BaseModel, Field, validator


class FrameGrabInput(BaseModel):
    video_uri: str
    mode: Literal["auto", "manual"]
    frame_every_n_seconds: float | None = None
    max_frames: int | None = None
    timestamps_ms: List[int] | None = None
    output_dir: Path

    @validator("timestamps_ms", always=True)
    def _timestamps_required_for_manual(cls, v, values):
        if values.get("mode") == "manual" and not v:
            raise ValueError("timestamps_ms required for manual mode")
        return v

    @validator("frame_every_n_seconds", always=True)
    def _interval_required_for_auto(cls, v, values):
        if values.get("mode") == "auto" and (v is None or v <= 0):
            raise ValueError("frame_every_n_seconds must be set for auto mode")
        return v


class FrameGrabResult(BaseModel):
    timestamp_ms: int
    frame_path: Path
    meta: Dict[str, Any] = Field(default_factory=dict)


class FrameGrabOutput(BaseModel):
    frames: List[FrameGrabResult]
    video_meta: Dict[str, Any] = Field(default_factory=dict)
