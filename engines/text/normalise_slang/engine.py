"""Atomic engine: TEXT.NORMALISE.SLANG_V1"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class NormaliseSlangRequest:
    payloads: List[Dict[str, Any]]
    lexicon_path: str | None = None
    normalize_swears: bool = False


@dataclass
class NormaliseSlangResponse:
    normalized: List[Dict[str, Any]]


def run(request: NormaliseSlangRequest) -> NormaliseSlangResponse:
    # TODO: port slang normalization logic in Phase 3
    return NormaliseSlangResponse(normalized=request.payloads)
