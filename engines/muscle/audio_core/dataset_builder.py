"""Build simple JSONL datasets from ASR results."""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, Any, List, Tuple


def _segments_from_asr(asr_results: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    for res in asr_results:
        for seg in res.get("segments", []) or []:
            text = (seg.get("text") or "").strip()
            if not text:
                continue
            pairs.append((res.get("file", ""), text))
    return pairs


def build_dataset(asr_results: List[Dict[str, Any]], output_dir: Path) -> Dict[str, Path | int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    pairs = _segments_from_asr(asr_results)
    samples = [
        {
            "system": "You are a lyrics data prep helper.",
            "input": {"source": fname},
            "output": {"text": text},
        }
        for fname, text in pairs
    ]
    random.shuffle(samples)
    val_size = max(1, int(0.1 * len(samples))) if samples else 0
    val_samples = samples[:val_size]
    train_samples = samples[val_size:]
    train_path = output_dir / "train.jsonl" if train_samples else None
    val_path = output_dir / "val.jsonl" if val_samples else None
    if train_path:
        train_path.write_text("\n".join(json.dumps(s, ensure_ascii=False) for s in train_samples), encoding="utf-8")
    if val_path:
        val_path.write_text("\n".join(json.dumps(s, ensure_ascii=False) for s in val_samples), encoding="utf-8")
    return {"train_path": train_path, "val_path": val_path, "total_samples": len(samples)}
