from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic import BaseModel, validator


class PackJsonlInput(BaseModel):
    bars_files: List[Path]
    output_dir: Path

    @validator("bars_files")
    def _not_empty(cls, v: List[Path]) -> List[Path]:
        if not v:
            raise ValueError("bars_files cannot be empty")
        for p in v:
            if not p.exists():
                raise FileNotFoundError(p)
        return v


class PackJsonlOutput(BaseModel):
    train_path: Path | None
    val_path: Path | None
    total_samples: int
