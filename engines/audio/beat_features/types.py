from __future__ import annotations

from pathlib import Path
from typing import Dict

from pydantic import BaseModel, validator


class BeatFeaturesInput(BaseModel):
    audio_paths: list[Path]

    @validator("audio_paths")
    def _not_empty(cls, v):
        if not v:
            raise ValueError("audio_paths cannot be empty")
        for p in v:
            if not p.exists():
                raise FileNotFoundError(p)
        return v


class BeatMetadata(BaseModel):
    bpm: float
    downbeats: list[float]
    grid16: float


class BeatFeaturesOutput(BaseModel):
    features: Dict[Path, BeatMetadata]
