"""CLI runner for TRAIN.LORA.PEFT_HF_V1."""
from __future__ import annotations

import argparse
from pathlib import Path

from engines.train.lora_peft_hf.engine import run
from engines.train.lora_peft_hf.types import LoraPeftHFInput


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PEFT/HF LoRA training (stub/demo)")
    parser.add_argument("train_jsonl", type=Path)
    parser.add_argument("val_jsonl", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--base-model", default="meta-llama/Meta-Llama-3-8B-Instruct")
    parser.add_argument("--config", type=str, default="{}", help="JSON string for extra config")
    args = parser.parse_args()
    import json

    cfg = json.loads(args.config)
    res = run(LoraPeftHFInput(train_jsonl=args.train_jsonl, val_jsonl=args.val_jsonl, output_dir=args.output_dir, base_model=args.base_model, config=cfg))
    print(f"Metadata -> {res.metadata_path}")


if __name__ == "__main__":
    main()
