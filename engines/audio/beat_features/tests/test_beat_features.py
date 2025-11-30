from pathlib import Path
from engines.audio.beat_features.engine import run, BeatFeaturesRequest


def test_beat_features_placeholder(tmp_path: Path) -> None:
    resp = run(BeatFeaturesRequest(audio_paths=[]))
    assert resp.features == {}
