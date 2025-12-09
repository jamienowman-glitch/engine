from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic import BaseModel, validator


class IngestLocalFileInput(BaseModel):
    files: List[Path]
    dest_dir: Path
    tenantId: str = "t_unknown"

    @validator("files")
    def _files_exist(cls, v: List[Path]) -> List[Path]:
        for path in v:
            if not path.exists():
                raise FileNotFoundError(path)
        return v


class IngestLocalFileOutput(BaseModel):
    staged_files: List[Path]
    uploaded_urls: List[str] | None = None
