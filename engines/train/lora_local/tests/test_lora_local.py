from pathlib import Path
from engines.train.lora_local.engine import run, LoraLocalRequest


def test_lora_local_placeholder(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    resp = run(LoraLocalRequest(train_jsonl=tmp_path / "train.jsonl", val_jsonl=tmp_path / "val.jsonl", output_dir=out_dir))
    assert resp.metadata_path.exists()
