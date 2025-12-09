"""Atomic engine: TEXT.CLEAN.ASR_PUNCT_CASE_V1."""
from __future__ import annotations

import re
from typing import List

from engines.text.clean_asr_punct_case.types import CleanASRPunctCaseInput, CleanASRPunctCaseOutput

SENTENCE_END = re.compile(r"([.!?])")


def _clean_text(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return stripped
    # Basic sentence case
    cleaned = stripped[0].upper() + stripped[1:]
    if not SENTENCE_END.search(cleaned):
        cleaned += "."
    return cleaned


def run(config: CleanASRPunctCaseInput) -> CleanASRPunctCaseOutput:
    cleaned: List[str] = [_clean_text(t) for t in config.texts]
    return CleanASRPunctCaseOutput(cleaned_texts=cleaned)
