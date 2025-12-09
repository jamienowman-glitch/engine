"""Atomic engine: TEXT.NORMALISE.SLANG_V1."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List

from engines.text.normalise_slang.types import NormaliseSlangInput, NormaliseSlangOutput


def _load_lexicon(lex_path: Path) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if lex_path.exists():
        with lex_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip() or line.startswith("#"):
                    continue
                try:
                    variant, canonical = line.rstrip("\n").split("\t", 1)
                    mapping[variant.lower()] = canonical.strip().lower()
                except ValueError:
                    continue
    return mapping


def _normalize_text(text: str, mapping: Dict[str, str]) -> str:
    base = (text or "").lower()
    for variant, canonical in mapping.items():
        base = base.replace(variant, canonical)
    return base.strip()


def run(config: NormaliseSlangInput) -> NormaliseSlangOutput:
    mapping: Dict[str, str] = {}
    if config.lexicon_path:
        mapping = _load_lexicon(config.lexicon_path)
    normalized_payloads: List[Dict[str, Any]] = []
    for payload in config.payloads:
        data = payload.copy()
        segments = data.get("segments") or []
        for segment in segments:
            text = segment.get("text", "") or ""
            norm = _normalize_text(text, mapping)
            segment["text_norm"] = norm
            segment["norm_applied"] = norm != text.lower()
        normalized_payloads.append(data)
    return NormaliseSlangOutput(normalized=normalized_payloads)
