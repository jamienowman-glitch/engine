from pathlib import Path
from engines.train.lora_peft_hf.engine import run, LoraPeftHFRequest


def test_lora_peft_hf_placeholder(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    resp = run(
        LoraPeftHFRequest(
            train_jsonl=tmp_path / "train.jsonl",
            val_jsonl=tmp_path / "val.jsonl",
            output_dir=out_dir,
            base_model="base",
            config={},
        )
    )
    assert resp.metadata_path.exists()
