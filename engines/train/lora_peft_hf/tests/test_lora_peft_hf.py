from pathlib import Path

import pytest

from engines.train.lora_peft_hf.engine import run
from engines.train.lora_peft_hf.types import LoraPeftHFInput, LoraPeftHFOutput


def test_lora_peft_hf_writes_metadata(tmp_path: Path) -> None:
    train = tmp_path / "train.jsonl"
    val = tmp_path / "val.jsonl"
    train.write_text("{}\n", encoding="utf-8")
    val.write_text("{}\n", encoding="utf-8")
    out_dir = tmp_path / "out"
    res = run(LoraPeftHFInput(train_jsonl=train, val_jsonl=val, output_dir=out_dir, base_model="base", config={}))
    assert isinstance(res, LoraPeftHFOutput)
    assert res.metadata_path.exists()


def test_lora_peft_hf_requires_files(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        LoraPeftHFInput(train_jsonl=tmp_path / "missing.jsonl", val_jsonl=tmp_path / "val.jsonl", output_dir=tmp_path, base_model="base", config={})
