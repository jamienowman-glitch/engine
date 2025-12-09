from pathlib import Path

from engines.audio_core import lora_train


def test_lora_train_stub_when_no_torch(monkeypatch, tmp_path: Path) -> None:
    # Force torch unavailable
    monkeypatch.setattr(lora_train, "torch", None)
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"output_dir": "' + str(tmp_path / 'out') + '"}', encoding="utf-8")
    res = lora_train.train_lora(cfg)
    assert res["status"] == "unavailable"
    assert Path(res["metadata_path"]).exists()


def test_lora_train_metadata_written(tmp_path: Path) -> None:
    # Use fallback if torch missing in env; test only metadata write path
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"output_dir": "' + str(tmp_path / 'out') + '"}', encoding="utf-8")
    res = lora_train.train_lora(cfg)
    assert Path(res["metadata_path"]).exists()
