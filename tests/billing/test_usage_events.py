from datetime import datetime, timezone

import pytest

from engines.budget.models import UsageEvent
from engines.budget.repository import FilesystemBudgetUsageRepository
from engines.budget.service import BudgetService
from engines.common.identity import RequestContext
from engines.logging.events.contract import StorageClass


@pytest.mark.parametrize("tool_type,tool_id", [("embedding", "vector_explorer"), ("search", "vector_explorer.search")])
def test_filesystem_usage_persists_across_instances(tmp_path, tool_type, tool_id):
    root = tmp_path / "usage_store"
    ctx = RequestContext(
        tenant_id="t_cost",
        env="dev",
        mode="saas",
        project_id="p_cost",
        request_id="req_usage",
    )
    first_repo = FilesystemBudgetUsageRepository(root=str(root))
    service = BudgetService(repo=first_repo)
    service.record_usage(
        ctx,
        [
            UsageEvent(
                tenant_id=ctx.tenant_id,
                env=ctx.env,
                surface="vector_explorer",
                provider="vertex",
                model_or_plan_id="gemini-test",
                tool_type=tool_type,
                tool_id=tool_id,
                tokens_input=5,
                tokens_output=0,
                cost=0,
            )
        ],
    )

    later_repo = FilesystemBudgetUsageRepository(root=str(root))
    later_service = BudgetService(repo=later_repo)
    later_ctx = RequestContext(
        tenant_id=ctx.tenant_id,
        env=ctx.env,
        mode="saas",
        project_id=ctx.project_id,
        request_id="req_usage_2",
    )
    later_service.record_usage(
        later_ctx,
        [
            UsageEvent(
                tenant_id=ctx.tenant_id,
                env=ctx.env,
                surface="vector_explorer",
                provider="vertex",
                model_or_plan_id="gemini-test",
                tool_type="usage",
                tool_id="vector_explorer.usage",
                tokens_input=3,
                tokens_output=0,
                cost=0,
            )
        ],
    )

    records = later_repo.list_usage(
        tenant_id=ctx.tenant_id,
        env=ctx.env,
        since=datetime.fromtimestamp(0, tz=timezone.utc),
        until=datetime.now(timezone.utc),
        limit=10,
    )
    assert len(records) == 2
    stateful = records[0]
    assert stateful.mode == ctx.mode
    assert stateful.project_id == ctx.project_id
    assert stateful.request_id == ctx.request_id
    assert stateful.trace_id == ctx.request_id
    assert stateful.run_id == ctx.request_id
    assert stateful.step_id.startswith("usage")
    assert stateful.storage_class == StorageClass.COST
