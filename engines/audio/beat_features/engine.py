"""Atomic engine: AUDIO.BEAT.FEATURES_V1 using librosa with graceful fallback."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

try:
    import librosa  # type: ignore
except Exception:  # pragma: no cover
    librosa = None  # type: ignore

from engines.audio.beat_features.types import BeatFeaturesInput, BeatFeaturesOutput, BeatMetadata


def _analyze(path: Path) -> BeatMetadata:
    if librosa is None:
        return BeatMetadata(bpm=0.0, downbeats=[], grid16=0.0)
    y, sr = librosa.load(path, sr=44100, mono=True)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
    downbeats = [float(b) for i, b in enumerate(beats) if i % 4 == 0]
    grid16 = 60.0 / (tempo * 4.0) if tempo else 0.0
    return BeatMetadata(bpm=float(tempo), downbeats=downbeats, grid16=float(grid16))


def run(config: BeatFeaturesInput) -> BeatFeaturesOutput:
    features: Dict[Path, BeatMetadata] = {}
    for path in config.audio_paths:
        features[path] = _analyze(path)
    return BeatFeaturesOutput(features=features)
