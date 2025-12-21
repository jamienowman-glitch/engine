from datetime import datetime, timedelta, timezone

from engines.common.identity import RequestContext
from engines.temperature.models import FloorConfig, TemperatureWeights
from engines.temperature.service import TemperatureService, TemperatureMetricsAdapter, InMemoryMetricsAdapter
from engines.temperature.repository import InMemoryTemperatureRepository
from engines.budget.repository import InMemoryBudgetUsageRepository
from engines.budget.models import UsageEvent


class StubMetricsAdapter(TemperatureMetricsAdapter):
    source_id = "stub"

    def __init__(self):
        self.called = False

    def fetch_metrics(self, ctx, surface, window_start, window_end, metric_keys=None):
        self.called = True
        return {"m1": 10.0}


def test_temperature_uses_adapter_when_provided():
    adapter = StubMetricsAdapter()
    svc = TemperatureService(repo=InMemoryTemperatureRepository(), usage_repo=InMemoryBudgetUsageRepository(), metrics_adapter=adapter)
    ctx = RequestContext(request_id="r", tenant_id="t_test", env="dev")
    weights = TemperatureWeights(tenant_id=ctx.tenant_id, env=ctx.env, surface="s", weights={"m1": 1.0})
    svc.repo.upsert_weights(weights)
    snap = svc.compute_temperature(ctx, surface="s", window_days=1)
    assert adapter.called
    assert snap.value == 10.0
    assert snap.source == "stub"


def test_temperature_in_memory_adapter_rolls_up_usage():
    usage_repo = InMemoryBudgetUsageRepository()
    now = datetime.now(timezone.utc)
    usage_repo.record_usage(
        UsageEvent(
            tenant_id="t_test",
            env="dev",
            surface="s",
            provider="vertex",
            model_or_plan_id="text",
            tokens_input=0,
            tokens_output=0,
            cost=0,
            metadata={"m1": 5.0},
            created_at=now,
        )
    )
    svc = TemperatureService(
        repo=InMemoryTemperatureRepository(),
        usage_repo=usage_repo,
        metrics_adapter=InMemoryMetricsAdapter(usage_repo),
    )
    ctx = RequestContext(request_id="r", tenant_id="t_test", env="dev")
    svc.repo.upsert_weights(TemperatureWeights(tenant_id=ctx.tenant_id, env=ctx.env, surface="s", weights={"m1": 1.0}))
    snap = svc.compute_temperature(ctx, surface="s", window_days=1)
    assert snap.value == 5.0
    assert snap.source == "in_memory"
