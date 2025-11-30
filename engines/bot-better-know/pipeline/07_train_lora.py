"""Placeholder LoRA trainer that records dataset metadata."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for _ in handle if _.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description="Record training metadata for LoRA runs")
    parser.add_argument("train_jsonl", help="Path to train.jsonl")
    parser.add_argument("val_jsonl", help="Path to val.jsonl")
    parser.add_argument("output_dir", help="Directory to store adapter artifacts")
    args = parser.parse_args()

    train_path = Path(args.train_jsonl)
    val_path = Path(args.val_jsonl)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "base_model": os.getenv("BASE_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct"),
        "train_examples": count_lines(train_path),
        "val_examples": count_lines(val_path),
        "notes": "Placeholder artifact. Replace with actual LoRA training when infra is ready.",
    }
    with (out_dir / "adapter_config.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)
    print(f"Recorded metadata -> {out_dir}")


if __name__ == "__main__":
    main()
