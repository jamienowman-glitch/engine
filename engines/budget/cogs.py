"""Cost-of-goods-sold estimation helpers."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional

from engines.budget.models import UsageEvent
from engines.budget.service import BudgetService, get_budget_service


# Simple price tables (extendable). Values are USD per unit (token or flat).
GCP_PRICE_TABLE = {
    "vertex/gemini-1.5-flash-002": Decimal("0.0000015"),  # per token example
}


@dataclass
class CreditPrior:
    tenant_id: str
    env: str
    provider: str
    credits_usd: Decimal


class CostEstimator:
    def __init__(self, budget_service: Optional[BudgetService] = None) -> None:
        self._budget = budget_service or get_budget_service()
        self._priors: Dict[tuple[str, str, str], CreditPrior] = {}

    def set_credit_prior(self, tenant_id: str, env: str, provider: str, credits_usd: Decimal) -> CreditPrior:
        prior = CreditPrior(tenant_id=tenant_id, env=env, provider=provider.lower(), credits_usd=credits_usd)
        self._priors[(tenant_id, env, prior.provider)] = prior
        return prior

    def get_credit_prior(self, tenant_id: str, env: str, provider: str) -> Optional[CreditPrior]:
        return self._priors.get((tenant_id, env, provider.lower()))

    def estimate_event_cost(self, ev: UsageEvent) -> Decimal:
        provider = (ev.provider or "").lower()
        if provider == "gcp" and ev.model_or_plan_id:
            key = f"{provider}/{ev.model_or_plan_id}"
            price = GCP_PRICE_TABLE.get(key)
            if price:
                tokens = Decimal(ev.tokens_input or 0) + Decimal(ev.tokens_output or 0)
                return tokens * price
        # AWS/Azure stub: rely on provided cost if present.
        if ev.cost:
            return Decimal(ev.cost)
        return Decimal("0")

    def summarize(self, tenant_id: str, env: str, window_days: int = 30) -> Dict[str, object]:
        ctx = self._budget.__class__.__name__  # not used; budget methods take ctx, so we'll synthesize
        class _Ctx:
            def __init__(self, tenant_id: str, env: str):
                self.tenant_id = tenant_id
                self.env = env

        context = _Ctx(tenant_id, env)
        # Use existing summary for provider/model totals
        provider_summary = self._budget.summary(context, window_days=window_days, group_by="provider")
        model_summary = self._budget.summary(context, window_days=window_days, group_by="model_or_plan_id")

        # Remaining credits per provider
        remaining = {}
        for provider, data in provider_summary.get("grouped", {}).items():
            prior = self.get_credit_prior(tenant_id, env, provider)
            credits = prior.credits_usd if prior else None
            remaining[provider] = {
                "credits_usd": float(credits) if credits is not None else None,
                "spend_usd": data.get("cost", 0.0),
                "estimated_remaining": (float(credits - Decimal(data.get("cost", 0.0))) if credits is not None else None),
            }
        # Azure placeholder
        if "azure" not in remaining:
            remaining["azure"] = {"credits_usd": None, "spend_usd": 0.0, "estimated_remaining": None, "note": "azure_not_configured"}

        return {
            "providers": remaining,
            "provider_summary": provider_summary,
            "model_summary": model_summary,
        }
