"""Atomic engine: DATASET.PACK.JSONL_V1."""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, Any, List

from engines.dataset.pack_jsonl.types import PackJsonlInput, PackJsonlOutput


def _load_bars(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data.get("bars", []) if isinstance(data, dict) else []


def run(config: PackJsonlInput) -> PackJsonlOutput:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    samples: List[Dict[str, Any]] = []
    for bars_file in config.bars_files:
        for bar in _load_bars(bars_file):
            samples.append({"input": {"flow": bar.get("flow_pred")}, "output": {"bar": bar.get("text")}})  # type: ignore[dict-item]

    random.shuffle(samples)
    val_size = max(1, int(0.1 * len(samples))) if samples else 0
    val_samples = samples[:val_size]
    train_samples = samples[val_size:]

    train_path = config.output_dir / "train.jsonl" if train_samples else None
    val_path = config.output_dir / "val.jsonl" if val_samples else None
    if train_path:
        train_path.write_text("\n".join(json.dumps(obj) for obj in train_samples), encoding="utf-8")
    if val_path:
        val_path.write_text("\n".join(json.dumps(obj) for obj in val_samples), encoding="utf-8")
    return PackJsonlOutput(train_path=train_path, val_path=val_path, total_samples=len(samples))
