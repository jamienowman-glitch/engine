"""Atomic engine: TRAIN.LORA.PEFT_HF_V1"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any


@dataclass
class LoraPeftHFRequest:
    train_jsonl: Path
    val_jsonl: Path
    output_dir: Path
    base_model: str
    config: Dict[str, Any]


@dataclass
class LoraPeftHFResponse:
    adapter_path: Optional[Path]
    metadata_path: Path


def run(request: LoraPeftHFRequest) -> LoraPeftHFResponse:
    request.output_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = request.output_dir / "peft_metadata.json"
    # TODO: implement PEFT training or realistic stub in Phase 4
    metadata_path.touch()
    return LoraPeftHFResponse(adapter_path=None, metadata_path=metadata_path)
