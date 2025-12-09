"""CLI runner for TRAIN.LORA.LOCAL_V1."""
from __future__ import annotations

import argparse
from pathlib import Path

from engines.train.lora_local.engine import run
from engines.train.lora_local.types import LoraLocalInput


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local LoRA metadata trainer")
    parser.add_argument("train_jsonl", type=Path)
    parser.add_argument("val_jsonl", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--base-model", default="meta-llama/Meta-Llama-3-8B-Instruct")
    args = parser.parse_args()
    res = run(LoraLocalInput(train_jsonl=args.train_jsonl, val_jsonl=args.val_jsonl, output_dir=args.output_dir, base_model=args.base_model))
    print(f"Metadata -> {res.metadata_path}")


if __name__ == "__main__":
    main()
