"""Atomic engine: TRAIN.LORA.LOCAL_V1"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class LoraLocalRequest:
    train_jsonl: Path
    val_jsonl: Path
    output_dir: Path
    base_model: str = "meta-llama/Meta-Llama-3-8B-Instruct"


@dataclass
class LoraLocalResponse:
    adapter_path: Optional[Path]
    metadata_path: Path


def run(request: LoraLocalRequest) -> LoraLocalResponse:
    request.output_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = request.output_dir / "adapter_config.json"
    # TODO: port stub metadata writer in Phase 3
    metadata_path.touch()
    return LoraLocalResponse(adapter_path=None, metadata_path=metadata_path)
