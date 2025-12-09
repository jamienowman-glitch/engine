from __future__ import annotations

from typing import List

from pydantic import BaseModel, validator


class CleanASRPunctCaseInput(BaseModel):
    texts: List[str]

    @validator("texts")
    def _not_empty(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("texts cannot be empty")
        return v


class CleanASRPunctCaseOutput(BaseModel):
    cleaned_texts: List[str]
