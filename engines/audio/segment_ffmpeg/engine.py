"""Atomic engine: AUDIO.SEGMENT.FFMPEG_V1"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class SegmentFFmpegRequest:
    input_path: Path
    output_dir: Path
    segment_seconds: int = 90
    overlap_seconds: int = 0


@dataclass
class SegmentMetadata:
    path: Path
    start_seconds: float
    end_seconds: float


@dataclass
class SegmentFFmpegResponse:
    segments: List[SegmentMetadata]


def run(request: SegmentFFmpegRequest) -> SegmentFFmpegResponse:
    request.output_dir.mkdir(parents=True, exist_ok=True)
    # TODO: extract ffmpeg segmentation logic in Phase 3
    return SegmentFFmpegResponse(segments=[])
