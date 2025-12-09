from __future__ import annotations

from engines.safety.adapter import GuardrailAdapter
from engines.safety.schemas import SafetyContext


def _ctx():
    return SafetyContext(tenant_id="t_demo", actor="user1", tools=["tool"], nexus_refs={})


def test_pass_when_all_pass():
    logged = []

    def logger(v):
        logged.append(v)

    adapter = GuardrailAdapter(
        vendor_guardrail=lambda c, p: "pass",
        firearms_check=lambda c, p: "pass",
        three_wise_check=lambda c, p: "pass",
        verdict_logger=logger,
    )
    verdict = adapter.evaluate(_ctx(), {"action": "read"})
    assert verdict.result == "pass"
    assert logged and logged[0].result == "pass"


def test_soft_warn_when_any_warn():
    adapter = GuardrailAdapter(
        vendor_guardrail=lambda c, p: "soft_warn",
        firearms_check=lambda c, p: "pass",
        three_wise_check=lambda c, p: "pass",
    )
    verdict = adapter.evaluate(_ctx(), {"action": "write"})
    assert verdict.result == "soft_warn"
    assert "vendor_warn" in verdict.reasons


def test_hard_block_overrides_warns():
    adapter = GuardrailAdapter(
        vendor_guardrail=lambda c, p: "soft_warn",
        firearms_check=lambda c, p: "hard_block",
        three_wise_check=lambda c, p: "pass",
    )
    verdict = adapter.evaluate(_ctx(), {"action": "execute"})
    assert verdict.result == "hard_block"
    assert "firearms_block" in verdict.reasons

