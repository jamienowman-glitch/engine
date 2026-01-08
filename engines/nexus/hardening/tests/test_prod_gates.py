"""Tests for Phase 9 Production Gates."""
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from engines.budget.repository import InMemoryBudgetPolicyRepository
from engines.common.identity import RequestContext
from engines.kill_switch.models import KillSwitch, KillSwitchUpdate
from engines.kill_switch.service import KillSwitchService
from engines.kill_switch.repository import InMemoryKillSwitchRepository
from engines.nexus.hardening.gate_chain import GateChain


@pytest.fixture(autouse=True)
def fake_strategy_policy_tabular(monkeypatch):
    class FakeTabularStoreService:
        _tables: dict[str, dict[str, dict]] = {}

        def __init__(self, context, resource_kind="strategy_policy_store"):
            self.context = context
            self.resource_kind = resource_kind

        def upsert(self, table_name, key, data):
            table = FakeTabularStoreService._tables.setdefault(table_name, {})
            table[key] = data

        def get(self, table_name, key):
            return FakeTabularStoreService._tables.get(table_name, {}).get(key)

        def list_by_prefix(self, table_name, key_prefix):
            table = FakeTabularStoreService._tables.get(table_name, {})
            return [record for k, record in table.items() if k.startswith(key_prefix)]

    FakeTabularStoreService._tables = {}
    monkeypatch.setattr("engines.strategy_lock.policy.TabularStoreService", FakeTabularStoreService)
from engines.nexus.hardening.rate_limit import RateLimitService

# Mock Dependencies
def mock_get_context():
    # Helper to return a context; normally injected by test client overrides
    pass

# We will test the logical components mostly, as full integration requires wiring the app
# But we can test the behavior of the controls isolated and then simulates logic.

def test_kill_switch_blocking():
    repo = InMemoryKillSwitchRepository()
    service = KillSwitchService(repo=repo)
    
    ctx = RequestContext(tenant_id="t_blocked", env="prod", user_id="u1")
    
    # 1. By default allowed
    service.ensure_action_allowed(ctx, "nexus_read")
    
    # 2. Block 'nexus_read'
    service.upsert(ctx, KillSwitchUpdate(disabled_actions=["nexus_read"]))
    
    with pytest.raises(HTTPException) as exc:
        service.ensure_action_allowed(ctx, "nexus_read")
    assert exc.value.status_code == 403
    
    # 3. Other actions allowed
    service.ensure_action_allowed(ctx, "other_action")


def test_rate_limiter():
    limiter = RateLimitService()
    ctx = RequestContext(tenant_id="t_spam", env="dev", user_id="u1")
    
    # Limit to 5 per 1 sec
    limit = 5
    window = 1.0
    
    for _ in range(5):
        limiter.check_rate_limit(ctx, action="test_action", limit=limit, window=window)
        
    # 6th should fail
    with pytest.raises(HTTPException) as exc:
        limiter.check_rate_limit(ctx, action="test_action", limit=limit, window=window)
    assert exc.value.status_code == 429

    
def test_tenancy_isolation_in_limits():
    """Verify rate limits don't leak across tenants."""
    limiter = RateLimitService()
    ctx1 = RequestContext(tenant_id="t_1", env="dev", user_id="u1")
    ctx2 = RequestContext(tenant_id="t_2", env="dev", user_id="u2")
    
    limit = 1
    
    # T1 uses quota
    limiter.check_rate_limit(ctx1, "act", limit=1, window=10)
    
    # T2 should still work
    limiter.check_rate_limit(ctx2, "act", limit=1, window=10)
    
    with pytest.raises(HTTPException):
        limiter.check_rate_limit(ctx1, "act", limit=1, window=10)


def test_gate_chain_requires_budget_policy():
    repo = InMemoryBudgetPolicyRepository()
    gate_chain = GateChain(
        kill_switch_service=_AllowAllKillSwitch(),
        firearms_service=_AllowAllFirearms(),
        strategy_lock_service=_AllowAllStrategyLock(),
        budget_service=_StubBudgetService(),
        kpi_service=_AvailableKpiService(),
        temperature_service=_StableTemperatureService(),
        budget_policy_repo=repo,
    )
    ctx = RequestContext(
        tenant_id="t_gate",
        env="prod",
        user_id="u_gate",
        mode="lab",
        surface_id="cards",
        app_id="card_app",
    )

    with pytest.raises(HTTPException) as exc:
        gate_chain._enforce_budget(ctx, "cards", "act")
    detail = exc.value.detail["error"]
    assert detail["code"] == "budget_threshold_missing"
    assert detail["gate"] == "budget"
    assert detail["http_status"] == 403


class _AllowAllKillSwitch:
    def ensure_action_allowed(self, *args, **kwargs):
        return None


class _AllowAllFirearms:
    def require_licence_or_raise(self, *args, **kwargs):
        return None

    def check_access(self, *args, **kwargs):
        return SimpleNamespace(allowed=True, reason="pass", strategy_lock_required=False, required_license_types=[])


class _AllowAllStrategyLock:
    def require_strategy_lock_or_raise(self, *args, **kwargs):
        return None


class _StubBudgetService:
    def summary(self, ctx, surface=None):
        return {"total_cost": Decimal("0"), "total_events": 0, "grouped": {}}


class _AvailableKpiService:
    def list_corridors(self, ctx, surface):
        return [SimpleNamespace(kpi_name="kpi_demo", floor=None, ceiling=None)]

    def latest_raw_measurement(self, ctx, surface, kpi_name):
        return None


class _StableTemperatureService:
    def compute_temperature(self, ctx, surface):
        return SimpleNamespace(floors_breached=[], ceilings_breached=[])
