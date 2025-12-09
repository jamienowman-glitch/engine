from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any

from pydantic import BaseModel, validator


class NormaliseSlangInput(BaseModel):
    payloads: List[Dict[str, Any]]
    lexicon_path: Path | None = None
    normalize_swears: bool = False

    @validator("payloads")
    def _payloads_not_empty(cls, v: List[Dict[str, Any]]):
        if not v:
            raise ValueError("payloads cannot be empty")
        return v


class NormaliseSlangOutput(BaseModel):
    normalized: List[Dict[str, Any]]
