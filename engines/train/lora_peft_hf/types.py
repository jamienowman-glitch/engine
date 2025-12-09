from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

from pydantic import BaseModel, validator


class LoraPeftHFInput(BaseModel):
    train_jsonl: Path
    val_jsonl: Path
    output_dir: Path
    base_model: str
    config: Dict[str, Any]

    @validator("train_jsonl", "val_jsonl")
    def _exists(cls, v: Path) -> Path:
        if not v.exists():
            raise FileNotFoundError(v)
        return v


class LoraPeftHFOutput(BaseModel):
    adapter_path: Path | None
    metadata_path: Path
