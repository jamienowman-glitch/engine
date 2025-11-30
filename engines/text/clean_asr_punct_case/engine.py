"""Atomic engine: TEXT.CLEAN.ASR_PUNCT_CASE_V1"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List


@dataclass
class CleanASRPunctCaseRequest:
    texts: List[str]


@dataclass
class CleanASRPunctCaseResponse:
    cleaned_texts: List[str]


def run(request: CleanASRPunctCaseRequest) -> CleanASRPunctCaseResponse:
    # TODO: implement punctuation/casing restoration in Phase 4
    return CleanASRPunctCaseResponse(cleaned_texts=request.texts)
