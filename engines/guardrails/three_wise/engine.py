"""3-Wise LLM risk panel skeleton (policy-aware)."""
from __future__ import annotations

from engines.guardrails.three_wise.schemas import ThreeWiseCheckRequest, ThreeWiseCheckResult, ThreeWiseVote

RISKY_TERMS = {"firearms", "violence", "gambling", "adult"}


def run(request: ThreeWiseCheckRequest) -> ThreeWiseCheckResult:
    text = f"{request.proposed_action} {request.context}".lower()
    risk = 0.1
    notes = "ALLOW"
    if any(term in text for term in RISKY_TERMS):
        risk = 0.8
        notes = "RISKY_CONTENT"
    vote = ThreeWiseVote(model="policy-scan", risk=risk, notes=notes)
    return ThreeWiseCheckResult(votes=[vote], aggregate_risk=vote.risk)
