from __future__ import annotations

from typing import Dict, Any, List

from pydantic import BaseModel, validator


class AlignAudioTextBarsInput(BaseModel):
    asr_payloads: List[Dict[str, Any]]
    beat_metadata: Dict[str, Any]

    @validator("asr_payloads")
    def _not_empty(cls, v):
        if not v:
            raise ValueError("asr_payloads cannot be empty")
        return v


class BarEntry(BaseModel):
    bar_index: int
    text: str
    text_norm: str
    stress_slots_16: List[int] = []


class AlignAudioTextBarsOutput(BaseModel):
    bars: List[BarEntry]
