"""Strategy Lock engine with simple policy checks."""
from __future__ import annotations

from engines.guardrails.strategy_lock.schemas import StrategyDecision, StrategyDraft, StrategyScope

BLOCK_KEYWORDS = {"firearms", "violence", "hate"}
HITL_KEYWORDS = {"spend", "budget", "payment"}


def run(tenantId: str, env: str, surface: str, conversationContext: dict, scope: StrategyScope) -> StrategyDecision:
    """Apply lightweight guardrails to a proposed objective."""
    objective = scope.objective.lower()
    constraints = " ".join(scope.constraints).lower()
    notes = []

    if any(k in objective or k in constraints for k in BLOCK_KEYWORDS):
        draft = StrategyDraft(summary="Blocked due to prohibited content", steps=[])
        return StrategyDecision(approved=False, notes="BLOCK", draft=draft)

    if any(k in objective or k in constraints for k in HITL_KEYWORDS):
        notes.append("REQUIRE_HITL")

    draft = StrategyDraft(
        summary=f"Strategy draft for {scope.objective}",
        steps=["collect_signals", "align_with_policies", "execute_after_guardrail"],
    )
    note_text = ";".join(notes) if notes else "ALLOW"
    return StrategyDecision(approved=not notes, notes=note_text, draft=draft)
