from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic import BaseModel, validator


class IngestLocalInput(BaseModel):
    source_dir: Path
    work_dir: Path
    tenantId: str = "t_unknown"

    @validator("source_dir")
    def _source_exists(cls, v: Path) -> Path:
        if not v.exists():
            raise FileNotFoundError(v)
        return v


class IngestLocalOutput(BaseModel):
    staged_paths: List[Path]
    uploaded_urls: List[str] | None = None
