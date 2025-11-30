"""Atomic engine: AUDIO.PREPROCESS.BASIC_CLEAN_V1"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class PreprocessBasicCleanRequest:
    input_paths: List[Path]
    output_dir: Path


@dataclass
class PreprocessBasicCleanResponse:
    cleaned_paths: List[Path]


def run(request: PreprocessBasicCleanRequest) -> PreprocessBasicCleanResponse:
    request.output_dir.mkdir(parents=True, exist_ok=True)
    # TODO: implement cleaning (normalization/denoise) in Phase 4
    return PreprocessBasicCleanResponse(cleaned_paths=[])
