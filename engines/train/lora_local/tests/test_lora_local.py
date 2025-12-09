from pathlib import Path

import pytest

from engines.train.lora_local.engine import run
from engines.train.lora_local.types import LoraLocalInput, LoraLocalOutput


def test_lora_local_writes_metadata(tmp_path: Path) -> None:
    train = tmp_path / "train.jsonl"
    val = tmp_path / "val.jsonl"
    train.write_text("{}\n", encoding="utf-8")
    val.write_text("{}\n", encoding="utf-8")
    out_dir = tmp_path / "out"
    res = run(LoraLocalInput(train_jsonl=train, val_jsonl=val, output_dir=out_dir))
    assert isinstance(res, LoraLocalOutput)
    assert res.metadata_path.exists()


def test_lora_local_requires_files(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        LoraLocalInput(train_jsonl=tmp_path / "missing.jsonl", val_jsonl=tmp_path / "val.jsonl", output_dir=tmp_path)
