from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic import BaseModel, validator


class PreprocessBasicCleanInput(BaseModel):
    input_paths: List[Path]
    output_dir: Path

    @validator("input_paths")
    def _exists(cls, v: List[Path]) -> List[Path]:
        for p in v:
            if not p.exists():
                raise FileNotFoundError(p)
        return v


class PreprocessBasicCleanOutput(BaseModel):
    cleaned_paths: List[Path]
