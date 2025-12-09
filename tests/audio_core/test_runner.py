from pathlib import Path

from engines.audio_core import runner


def test_runner_pipeline(monkeypatch, tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    audio = raw_dir / "a.wav"
    audio.write_bytes(b"data")

    # stub preprocess to just copy
    monkeypatch.setattr(runner, "run_clean", lambda cfg: type("R", (), {"cleaned_paths": cfg.input_paths}))
    monkeypatch.setattr(runner, "run_beats", lambda cfg: type("B", (), {"features": {}}))
    monkeypatch.setattr(runner.asr_backend, "transcribe_audio", lambda paths: [{"file": paths[0].name, "segments": []}])
    monkeypatch.setattr(runner.dataset_builder, "build_dataset", lambda asr, out: {"train_path": out / "train.jsonl", "val_path": None, "total_samples": 0})
    monkeypatch.setattr(runner.lora_train, "train_lora", lambda cfg: {"status": "stub"})

    out = runner.run_pipeline(raw_dir, tmp_path / "work", lora_config=None)
    assert "dataset" in out
    assert out["lora"] is None
