from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any

from pydantic import BaseModel, Field, validator


class ASRWhisperInput(BaseModel):
    audio_paths: List[Path]
    model_name: str = "medium"
    compute_type: str = "int8"
    device: str = "cpu"

    @validator("audio_paths")
    def _require_files(cls, v: List[Path]) -> List[Path]:
        if not v:
            raise ValueError("audio_paths cannot be empty")
        for p in v:
            if not p.exists():
                raise FileNotFoundError(p)
        return v


class WordTiming(BaseModel):
    text: str
    start: float
    end: float


class SegmentResult(BaseModel):
    start: float
    end: float
    text: str
    words: List[WordTiming] = Field(default_factory=list)


class FileASRResult(BaseModel):
    file: str
    duration: float
    language: str
    segments: List[SegmentResult] = Field(default_factory=list)


class ASRWhisperOutput(BaseModel):
    results: List[FileASRResult]
