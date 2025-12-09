"""Atomic engine: TRAIN.LORA.PEFT_HF_V1 (stub)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from engines.train.lora_peft_hf.types import LoraPeftHFInput, LoraPeftHFOutput


def run(config: LoraPeftHFInput) -> LoraPeftHFOutput:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "base_model": config.base_model,
        "train_path": str(config.train_jsonl),
        "val_path": str(config.val_jsonl),
        "config": config.config,
        "notes": "stub PEFT/HF adapter",
    }
    metadata_path = config.output_dir / "peft_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return LoraPeftHFOutput(adapter_path=None, metadata_path=metadata_path)
