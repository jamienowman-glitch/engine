"""Atomic engine: DATASET.PACK.JSONL_V1"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any


@dataclass
class PackJsonlRequest:
    bars_files: List[Path]
    output_dir: Path


@dataclass
class PackJsonlResponse:
    train_path: Path | None
    val_path: Path | None
    total_samples: int


def run(request: PackJsonlRequest) -> PackJsonlResponse:
    request.output_dir.mkdir(parents=True, exist_ok=True)
    # TODO: port JSONL packing logic in Phase 3
    return PackJsonlResponse(train_path=None, val_path=None, total_samples=0)
