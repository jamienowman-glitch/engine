"""Utilities for grime slang-aware normalization."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

DEFAULT_LEXICON_PATH = "/app/pipeline/lex/slang_norm.tsv"
MODULE_ROOT = Path(__file__).resolve().parent
LOCAL_LEXICON_PATH = MODULE_ROOT / "lex" / "slang_norm.tsv"
SPACE_RE = re.compile(r"\s+")

# Common ASR mis-hearings for profanity that we only fix when explicitly granted.
SWEAR_MISHEARS = {
    r"\bducking\b": "fucking",
    r"\bmother trucker\b": "motherfucker",
    r"\bwitch\b": "bitch",
    r"\bshoot\b": "shit",
}


def _normalize_variant(raw: str) -> str:
    variant = raw.strip().lower()
    if "|" in variant and not variant.startswith("re:"):
        variant = variant.split("|", 1)[0].strip()
    return variant


@dataclass
class LexEntry:
    variant: str
    canonical: str
    pattern: re.Pattern[str]
    is_regex: bool
    token_count: int

    @classmethod
    def from_row(cls, variant_raw: str, canonical: str) -> "LexEntry":
        if variant_raw.startswith("re:"):
            expr = variant_raw[3:]
            pattern = re.compile(expr, re.IGNORECASE)
            token_count = 1  # best guess; regex could span but used for tokens too
            return cls(variant_raw, canonical, pattern, True, token_count)
        variant = _normalize_variant(variant_raw)
        tokens = [t for t in variant.split(" ") if t]
        if tokens:
            escaped_tokens = [re.escape(token) for token in tokens]
            body = r"\s+".join(escaped_tokens)
        else:
            body = re.escape(variant)
        pattern = re.compile(rf"\b{body}\b")
        token_count = len(tokens) if tokens else 1
        return cls(variant, canonical, pattern, False, token_count)

    def replace_text(self, text: str) -> Tuple[str, int]:
        return self.pattern.subn(self.canonical, text)

    def token_matches(self, token: str) -> bool:
        if self.is_regex:
            return bool(self.pattern.fullmatch(token))
        return token == self.variant


class SlangNormalizer:
    """Normalize grime slang without censoring the source."""

    def __init__(self, lexicon: Iterable[LexEntry], normalize_swears: bool = False) -> None:
        self.entries: List[LexEntry] = list(lexicon)
        if normalize_swears:
            for expr, canonical in SWEAR_MISHEARS.items():
                self.entries.append(LexEntry.from_row(f"re:{expr}", canonical))
        # token-level entries are only those with a single token or regex
        self.token_entries = [e for e in self.entries if e.token_count == 1]

    @staticmethod
    def _cleanup(text: str) -> str:
        return SPACE_RE.sub(" ", text).strip()

    def normalize_text(self, text: str) -> Tuple[str, bool]:
        lowered = (text or "").lower()
        updated = lowered
        changed = False
        for entry in self.entries:
            updated, n = entry.replace_text(updated)
            if n:
                changed = True
        cleaned = self._cleanup(updated)
        return cleaned, changed

    def normalize_token(self, token: str) -> Tuple[str, bool]:
        base = (token or "").lower()
        for entry in self.token_entries:
            if entry.token_matches(base):
                canonical = entry.canonical
                return canonical, canonical != base
        return base, False

    def normalize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        segments = payload.get("segments") or []
        for segment in segments:
            raw_text = segment.get("text", "")
            segment["text_raw"] = raw_text
            text_norm, text_changed = self.normalize_text(raw_text)
            segment["text_norm"] = text_norm
            any_word_change = False
            for word in segment.get("words", []) or []:
                word_text = word.get("text", "")
                normalized_word, word_changed = self.normalize_token(word_text)
                word["norm_applied"] = word_changed
                if word_changed:
                    word["norm"] = normalized_word
                else:
                    word.pop("norm", None)
                any_word_change = any_word_change or word_changed
            raw_lower = raw_text.lower()
            segment["norm_applied"] = text_changed or any_word_change or (text_norm != raw_lower)
        return payload


def load_lexicon(path: str | os.PathLike[str] | None = None) -> List[LexEntry]:
    lex_path = Path(path or DEFAULT_LEXICON_PATH)
    if not lex_path.exists() and LOCAL_LEXICON_PATH.exists():
        lex_path = LOCAL_LEXICON_PATH
    entries: List[LexEntry] = []
    if not lex_path.exists():
        raise FileNotFoundError(f"Lexicon not found: {lex_path}")
    with lex_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip() or line.strip().startswith("#"):
                continue
            try:
                variant, canonical = line.rstrip("\n").split("\t", 1)
            except ValueError:
                continue
            variant = variant.strip()
            canonical = canonical.strip().lower()
            if not variant or not canonical:
                continue
            entries.append(LexEntry.from_row(variant, canonical))
    return entries


def write_norm_file(payload: Dict[str, Any], source_path: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    src_str = str(source_path)
    if not src_str.endswith(".json"):
        raise ValueError("ASR payloads must be JSON files")
    norm_path = dest_dir / Path(src_str[:-5] + ".norm.json").name
    with norm_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return norm_path


__all__ = [
    "DEFAULT_LEXICON_PATH",
    "LexEntry",
    "SlangNormalizer",
    "load_lexicon",
    "write_norm_file",
]
