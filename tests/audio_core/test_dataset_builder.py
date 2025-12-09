from pathlib import Path

from engines.audio_core import dataset_builder


def test_dataset_builder_creates_jsonl(tmp_path: Path) -> None:
    asr = [{"file": "a.wav", "segments": [{"text": "hello"}, {"text": ""}]}]
    out = dataset_builder.build_dataset(asr, tmp_path / "ds")
    assert out["total_samples"] == 1
    assert out["train_path"] is not None
    assert out["train_path"].exists()
