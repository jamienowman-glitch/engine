"""Atomic engine: TRAIN.LORA.LOCAL_V1 (stub metadata writer)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from engines.train.lora_local.types import LoraLocalInput, LoraLocalOutput


def run(config: LoraLocalInput) -> LoraLocalOutput:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "base_model": config.base_model,
        "train_path": str(config.train_jsonl),
        "val_path": str(config.val_jsonl),
        "notes": "stub adapter metadata",
    }
    metadata_path = config.output_dir / "adapter_config.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return LoraLocalOutput(adapter_path=None, metadata_path=metadata_path)
