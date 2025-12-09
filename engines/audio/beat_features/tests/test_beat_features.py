from pathlib import Path

import pytest

from engines.audio import beat_features as mod
from engines.audio.beat_features.engine import run
from engines.audio.beat_features.types import BeatFeaturesInput, BeatFeaturesOutput, BeatMetadata


def test_beat_features_uses_librosa_when_available(monkeypatch, tmp_path: Path) -> None:
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"123")

    if mod.librosa is None:
        pytest.skip("librosa not installed")

    def fake_load(path, sr=44100, mono=True):  # type: ignore[no-untyped-def]
        return [0.1, 0.2], 44100

    def fake_beat_track(y, sr=44100, units="time"):  # type: ignore[no-untyped-def]
        return 120.0, [0.0, 0.5, 1.0, 1.5, 2.0]

    monkeypatch.setattr(mod.librosa, "load", fake_load)
    monkeypatch.setattr(mod.librosa, "beat_track", fake_beat_track)

    out = run(BeatFeaturesInput(audio_paths=[audio]))
    meta = list(out.features.values())[0]
    assert meta.bpm == 120.0
    assert meta.grid16 > 0


def test_beat_features_falls_back_without_librosa(monkeypatch, tmp_path: Path) -> None:
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"123")
    monkeypatch.setattr(mod, "librosa", None)
    out = run(BeatFeaturesInput(audio_paths=[audio]))
    meta = list(out.features.values())[0]
    assert meta.bpm == 0.0
    assert meta.downbeats == []


def test_beat_features_requires_files(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        BeatFeaturesInput(audio_paths=[])
