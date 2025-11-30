"""Atomic engine: VIDEO.INGEST.FRAME_GRAB_V1"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Literal


Mode = Literal["auto", "manual"]


@dataclass
class FrameGrabRequest:
    video_uri: str
    mode: Mode
    frame_every_n_seconds: float | None = None
    max_frames: int | None = None
    timestamps_ms: List[int] | None = None
    output_dir: Path | None = None


@dataclass
class FrameGrabResult:
    timestamp_ms: int
    frame_path: Path
    meta: Dict[str, Any]


@dataclass
class FrameGrabResponse:
    frames: List[FrameGrabResult]
    video_meta: Dict[str, Any]


def run(request: FrameGrabRequest) -> FrameGrabResponse:
    out_dir = request.output_dir or Path("tmp/frame_grab")
    out_dir.mkdir(parents=True, exist_ok=True)
    # TODO: implement ffmpeg-driven frame extraction in Phase 4
    return FrameGrabResponse(frames=[], video_meta={})
