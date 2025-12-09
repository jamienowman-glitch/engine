"""PII text stripping engine schemas (P-01.A/B)."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel


class PiiTextRequest(BaseModel):
    text: str
    mode: str = "strict"
    allowlist: List[str] = []


class DataPolicyDecision(BaseModel):
    train_ok: bool
    store_long_term_ok: bool
    reason: str = ""


class PiiTextResult(BaseModel):
    clean_text: str
    pii_flags: List[str]
    policy: DataPolicyDecision
