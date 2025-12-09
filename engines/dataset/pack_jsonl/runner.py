"""CLI runner for DATASET.PACK.JSONL_V1."""
from __future__ import annotations

import argparse
from pathlib import Path

from engines.dataset.pack_jsonl.engine import run
from engines.dataset.pack_jsonl.types import PackJsonlInput


def main() -> None:
    parser = argparse.ArgumentParser(description="Pack bars JSON into train/val JSONL")
    parser.add_argument("output_dir", type=Path, help="Output directory for train/val")
    parser.add_argument("bars_files", nargs="+", type=Path, help="Bars JSON files")
    args = parser.parse_args()
    res = run(PackJsonlInput(bars_files=args.bars_files, output_dir=args.output_dir))
    print(f"Samples: {res.total_samples} train={res.train_path} val={res.val_path}")


if __name__ == "__main__":
    main()
