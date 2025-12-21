from decimal import Decimal
from datetime import datetime, timezone, timedelta

from engines.budget.cogs import CostEstimator
from engines.budget.models import UsageEvent
from engines.budget.repository import InMemoryBudgetUsageRepository
from engines.budget.service import BudgetService, set_budget_service
from engines.common.identity import RequestContext


def _ctx():
    return RequestContext(tenant_id="t_demo", env="dev", user_id="u1")


def test_cost_estimator_with_priors():
    repo = InMemoryBudgetUsageRepository()
    svc = BudgetService(repo=repo)
    set_budget_service(svc)
    now = datetime.now(timezone.utc)
    repo.record_usage(
        UsageEvent(
            tenant_id="t_demo",
            env="dev",
            provider="aws",
            model_or_plan_id="lambda",
            cost=Decimal("2.5"),
            created_at=now - timedelta(days=1),
        )
    )
    est = CostEstimator(budget_service=svc)
    est.set_credit_prior("t_demo", "dev", "aws", Decimal("10"))
    summary = est.summarize("t_demo", "dev", window_days=7)
    assert summary["providers"]["aws"]["estimated_remaining"] == 7.5


def test_cost_estimator_gcp_price_table():
    repo = InMemoryBudgetUsageRepository()
    svc = BudgetService(repo=repo)
    set_budget_service(svc)
    now = datetime.now(timezone.utc)
    repo.record_usage(
        UsageEvent(
            tenant_id="t_demo",
            env="dev",
            provider="gcp",
            model_or_plan_id="gemini-1.5-flash-002",
            tokens_input=1000,
            tokens_output=500,
            cost=Decimal("0"),  # rely on estimator
            created_at=now - timedelta(days=1),
        )
    )
    est = CostEstimator(budget_service=svc)
    est.set_credit_prior("t_demo", "dev", "gcp", Decimal("5"))
    summary = est.summarize("t_demo", "dev", window_days=7)
    assert summary["providers"]["gcp"]["estimated_remaining"] is not None
    assert "azure" in summary["providers"]
