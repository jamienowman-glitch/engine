from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic import BaseModel, Field, validator


class SegmentFFmpegInput(BaseModel):
    input_path: Path
    output_dir: Path
    segment_seconds: int = Field(90, gt=0)
    overlap_seconds: int = Field(0, ge=0)

    @validator("input_path")
    def _path_exists(cls, v: Path) -> Path:
        if not v.exists():
            raise FileNotFoundError(v)
        return v


class SegmentMetadata(BaseModel):
    path: Path
    start_seconds: float
    end_seconds: float


class SegmentFFmpegOutput(BaseModel):
    segments: List[SegmentMetadata]
