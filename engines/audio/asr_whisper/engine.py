"""Atomic engine: AUDIO.ASR.WHISPER_V1"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any


@dataclass
class ASRWhisperRequest:
    audio_paths: List[Path]
    model_name: str = "medium"
    compute_type: str = "int8"
    device: str = "cpu"


@dataclass
class ASRWhisperResponse:
    results: List[Dict[str, Any]]


def run(request: ASRWhisperRequest) -> ASRWhisperResponse:
    # TODO: implement Whisper ASR extraction in Phase 3
    return ASRWhisperResponse(results=[])
