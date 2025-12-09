"""Guardrail adapter combining vendor guardrails with Firearms/3-Wise."""
from __future__ import annotations

from typing import Callable, Optional

from engines.safety.schemas import GuardrailVerdict, SafetyContext

VendorGuardrail = Callable[[SafetyContext, dict], str]
FirearmsCheck = Callable[[SafetyContext, dict], str]
ThreeWiseCheck = Callable[[SafetyContext, dict], str]
VerdictLogger = Callable[[GuardrailVerdict], None]


class GuardrailAdapter:
    def __init__(
        self,
        vendor_guardrail: Optional[VendorGuardrail] = None,
        firearms_check: Optional[FirearmsCheck] = None,
        three_wise_check: Optional[ThreeWiseCheck] = None,
        verdict_logger: Optional[VerdictLogger] = None,
    ) -> None:
        self._vendor_guardrail = vendor_guardrail
        self._firearms_check = firearms_check
        self._three_wise_check = three_wise_check
        self._verdict_logger = verdict_logger

    def evaluate(self, context: SafetyContext, payload: dict) -> GuardrailVerdict:
        vendor = self._vendor_guardrail(context, payload) if self._vendor_guardrail else "pass"
        firearms = self._firearms_check(context, payload) if self._firearms_check else "pass"
        three_wise = self._three_wise_check(context, payload) if self._three_wise_check else "pass"

        reasons = []
        result = "pass"
        for name, verdict in (("vendor", vendor), ("firearms", firearms), ("three_wise", three_wise)):
            if verdict == "hard_block":
                result = "hard_block"
                reasons.append(f"{name}_block")
            elif verdict == "soft_warn" and result != "hard_block":
                result = "soft_warn"
                reasons.append(f"{name}_warn")

        gr = GuardrailVerdict(
            vendor_verdict=vendor,
            firearms_verdict=firearms,
            three_wise_verdict=three_wise,
            result=result,
            reasons=reasons,
            tenant_id=context.tenant_id,
            agent_id=context.agent_id,
            episode_id=context.episode_id,
        )
        if self._verdict_logger:
            self._verdict_logger(gr)
        return gr
