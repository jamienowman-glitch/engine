"""PII redaction helpers used by Gate1 outbound boundaries."""

from __future__ import annotations

import re
from typing import Dict, Optional, Protocol

from engines.common.identity import RequestContext

_EMAIL_PATTERN = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", re.IGNORECASE
)
_PHONE_PATTERN = re.compile(
    r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
)
_SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CC_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,16}\b")

_PII_RULES = (
    ("email", _EMAIL_PATTERN, "[REDACTED_EMAIL]"),
    ("phone", _PHONE_PATTERN, "[REDACTED_PHONE]"),
    ("ssn", _SSN_PATTERN, "[REDACTED_SSN]"),
    ("credit_card", _CC_PATTERN, "[REDACTED_CC]"),
)


def redact_text(text: Optional[str]) -> tuple[str, Dict[str, bool], bool]:
    """
    Redact known PII patterns from the supplied text.

    Returns:
        sanitized_text: redacted payload
        pii_flags: mapping of detected PII kinds
        train_ok: False when any PII was removed
    """
    sanitized = text or ""
    flags: Dict[str, bool] = {}
    for label, pattern, placeholder in _PII_RULES:
        found = bool(pattern.search(sanitized))
        flags[label] = found
        if found:
            sanitized = pattern.sub(placeholder, sanitized)
    train_ok = not any(flags.values())
    return sanitized, flags, train_ok


class PIIRehydrationHook(Protocol):
    """
    Tenant-authorized hook to rehydrate masked payloads when needed.
    """

    def rehydrate(self, masked_text: str, ctx: RequestContext) -> str:
        """
        Return the tenant-authorized plaintext for the provided masked payload.
        """
        ...
