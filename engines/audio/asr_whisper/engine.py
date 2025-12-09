"""Atomic engine: AUDIO.ASR.WHISPER_V1 (structure-ready, stub inference)."""
from __future__ import annotations

from engines.audio.asr_whisper.types import (
    ASRWhisperInput,
    ASRWhisperOutput,
    FileASRResult,
    SegmentResult,
)


def run(config: ASRWhisperInput) -> ASRWhisperOutput:
    """Return structured ASR results; replace with real faster-whisper later."""
    results = []
    for path in config.audio_paths:
        results.append(
            FileASRResult(
                file=path.name,
                duration=0.0,
                language="en",
                segments=[SegmentResult(start=0.0, end=0.0, text="", words=[])],
            )
        )
    return ASRWhisperOutput(results=results)
