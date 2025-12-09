"""Atomic engine: ALIGN.AUDIO_TEXT.BARS_V1 (simplified)."""
from __future__ import annotations

from typing import Dict, Any, List

from engines.align.audio_text_bars.types import AlignAudioTextBarsInput, AlignAudioTextBarsOutput, BarEntry


def run(config: AlignAudioTextBarsInput) -> AlignAudioTextBarsOutput:
    bars: List[BarEntry] = []
    bar_idx = 1
    for payload in config.asr_payloads:
        for segment in payload.get("segments", []):
            text = (segment.get("text") or "").strip()
            if not text:
                continue
            norm = segment.get("text_norm") or text.lower()
            bars.append(BarEntry(bar_index=bar_idx, text=text, text_norm=norm, stress_slots_16=[]))
            bar_idx += 1
    return AlignAudioTextBarsOutput(bars=bars)
