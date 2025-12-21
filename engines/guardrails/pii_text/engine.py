"""Text PII strip engine (regex-based)."""
from __future__ import annotations

import re
from typing import List

from engines.guardrails.pii_text.schemas import DataPolicyDecision, PiiTextRequest, PiiTextResult

# Simple regexes for common PII
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")
CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
POSTAL_RE = re.compile(r"\b\d{5}(?:-\d{4})?\b")


def _mask(text: str, matches: List[re.Match]) -> str:
    masked = text
    for m in sorted(matches, key=lambda x: x.start(), reverse=True):
        masked = masked[: m.start()] + "[REDACTED]" + masked[m.end() :]
    return masked


def run(request: PiiTextRequest) -> PiiTextResult:
    text = request.text or ""
    flags: List[str] = []
    matches: List[re.Match] = []
    for label, regex in (
        ("email", EMAIL_RE),
        ("phone", PHONE_RE),
        ("card", CARD_RE),
        ("postal", POSTAL_RE),
    ):
        found = list(regex.finditer(text))
        if found:
            flags.append(label)
            matches.extend(found)
    clean_text = _mask(text, matches)
    policy = DataPolicyDecision(
        train_ok=not flags,
        store_long_term_ok=False,
        reason="pii_masked" if flags else "no_pii_detected",
    )
    return PiiTextResult(clean_text=clean_text, pii_flags=flags, policy=policy)
