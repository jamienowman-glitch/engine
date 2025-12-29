"""Audio core ASR backend wrapper.

Attempts to use faster-whisper if available; otherwise returns a structured
"unavailable" result so pipelines can proceed gracefully.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

try:  # optional dependency
    from faster_whisper import WhisperModel  # type: ignore
except Exception:  # pragma: no cover
    WhisperModel = None  # type: ignore


class ASRResult(Dict[str, Any]):
    pass


def _transcribe_file(model: Any, path: Path) -> ASRResult:
    segments, info = model.transcribe(
        str(path),
        vad_filter=True,
        word_timestamps=True,
        condition_on_previous_text=False,
        beam_size=1,
        best_of=1,
    )
    payload = {
        "file": path.name,
        "language": info.language,
        "duration": float(info.duration),
        "segments": [],
    }
    for seg in segments:
        words = [
            {"text": (w.word or "").strip(), "start": float(w.start), "end": float(w.end)}
            for w in (seg.words or [])
        ]
        payload["segments"].append(
            {"start": float(seg.start), "end": float(seg.end), "text": (seg.text or "").strip(), "words": words}
        )
    return payload


def transcribe_audio(paths: List[Path], model_name: str = "medium", device: str = "cpu", compute_type: str = "int8") -> List[ASRResult]:
    """Transcribe a list of audio paths using faster-whisper if present.

    If the dependency is missing, returns a structured unavailable result.
    """
    if WhisperModel is None:
        return [
            {
                "file": path.name,
                "status": "unavailable",
                "reason": "faster-whisper not installed",
                "segments": [],
                "duration": 0.0,
                "language": "",
            }
            for path in paths
        ]

    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    results: List[ASRResult] = []
    for path in paths:
        try:
            results.append(_transcribe_file(model, path))
        except Exception as exc:  # pragma: no cover
            results.append({"file": path.name, "status": "error", "reason": str(exc), "segments": []})
    return results
