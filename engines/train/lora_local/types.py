from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, validator


class LoraLocalInput(BaseModel):
    train_jsonl: Path
    val_jsonl: Path
    output_dir: Path
    base_model: str = "meta-llama/Meta-Llama-3-8B-Instruct"

    @validator("train_jsonl", "val_jsonl")
    def _exists(cls, v: Path) -> Path:
        if not v.exists():
            raise FileNotFoundError(v)
        return v


class LoraLocalOutput(BaseModel):
    adapter_path: Path | None
    metadata_path: Path
