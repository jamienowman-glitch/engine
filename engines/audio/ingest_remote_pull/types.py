from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic import BaseModel, HttpUrl, validator


class IngestRemotePullInput(BaseModel):
    uris: List[str]
    dest_dir: Path
    tenantId: str = "t_unknown"

    @validator("uris")
    def _require_uris(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("at least one URI is required")
        return v


class IngestRemotePullOutput(BaseModel):
    downloaded: List[Path]
    uploaded_urls: List[str] | None = None
