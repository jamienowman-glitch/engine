from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timedelta, timezone

from engines.budget.service import BudgetService
from engines.budget.repository import InMemoryBudgetUsageRepository
from engines.budget.models import UsageEvent
from engines.common.identity import RequestContext
from engines.budget import service as budget_service


def _ctx():
    return RequestContext(tenant_id="t_demo", env="dev", user_id="u1")


def test_record_and_list_usage():
    repo = InMemoryBudgetUsageRepository()
    svc = BudgetService(repo=repo)
    ctx = _ctx()
    rec = UsageEvent(
        tenant_id="t_demo",
        env="dev",
        provider="openai",
        model_or_plan_id="gpt-4o",
        tokens_input=1000,
        tokens_output=200,
        tool_type="embedding",
    )
    saved = svc.record_usage(ctx, [rec])
    assert saved[0].provider == "openai"
    listed = svc.query_usage(ctx, window_days=1)
    assert len(listed) == 1


def test_aggregate_summary_by_provider():
    repo = InMemoryBudgetUsageRepository()
    svc = BudgetService(repo=repo)
    ctx = _ctx()
    now = datetime.now(timezone.utc)
    repo.record_usage(
        UsageEvent(
            tenant_id="t_demo",
            env="dev",
            provider="openai",
            model_or_plan_id="gpt-4o",
            tokens_input=0,
            tokens_output=0,
            cost=Decimal("1.0"),
            created_at=now - timedelta(hours=1),
        )
    )
    repo.record_usage(
        UsageEvent(
            tenant_id="t_demo",
            env="dev",
            provider="vertex",
            model_or_plan_id="text-embedding-004",
            tokens_input=0,
            tokens_output=0,
            cost=Decimal("0.5"),
            created_at=now - timedelta(hours=2),
        )
    )
    summary = svc.summary(ctx, window_days=1)
    assert summary["total_events"] == 2
    assert summary["grouped"]["openai"]["count"] == 1


def test_record_usage_attaches_aws_metadata(monkeypatch):
    repo = InMemoryBudgetUsageRepository()
    svc = BudgetService(repo=repo)
    ctx = _ctx()

    monkeypatch.setattr(
        budget_service,
        "aws_identity",
        lambda: {"account_id": "123456789012", "arn": "arn:aws:iam::123:user/demo", "region": "us-east-1"},
    )
    rec = UsageEvent(
        tenant_id=ctx.tenant_id,
        env=ctx.env,
        provider="aws",
        cost=Decimal("0.1"),
    )
    saved = svc.record_usage(ctx, [rec])
    assert saved[0].metadata["aws_account_id"] == "123456789012"
    assert saved[0].metadata["aws_principal_arn"] == "arn:aws:iam::123:user/demo"
