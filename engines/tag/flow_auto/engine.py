"""Atomic engine: TAG.FLOW.AUTO_V1 (heuristic flow tagging)."""
from __future__ import annotations

from typing import Dict, Any, List

from engines.tag.flow_auto.types import FlowAutoInput, FlowAutoOutput, FlowPair


def _predict_flow(chunk: List[Dict[str, Any]]) -> str:
    if not chunk:
        return "unknown"
    syllables = [bar.get("syllables", 0) for bar in chunk]
    bpm_values = [bar.get("bpm") for bar in chunk if bar.get("bpm") is not None]
    bpm = sum(bpm_values) / len(bpm_values) if bpm_values else 140.0
    avg_syllables = sum(syllables) / len(syllables) if syllables else 0

    if avg_syllables < 12 or bpm < 132:
        return "half_time"
    if avg_syllables > 20 and bpm >= 132:
        return "triplet_machine"
    if 138 <= bpm <= 144:
        return "skippy_140"
    return "triplet_machine" if avg_syllables > 16 else "half_time"


def run(config: FlowAutoInput) -> FlowAutoOutput:
    flow_pairs: List[FlowPair] = []
    bars = config.bars
    for i in range(0, len(bars), 2):
        chunk = bars[i : i + 2]
        if not chunk:
            continue
        flow = _predict_flow(chunk)
        for bar in chunk:
            bar["flow_pred"] = flow
        flow_pairs.append(
            FlowPair(bar_start=chunk[0].get("bar_index", i + 1), bar_end=chunk[-1].get("bar_index", i + len(chunk)), flow_pred=flow)
        )
    return FlowAutoOutput(bars=bars, flow_pairs=flow_pairs)
