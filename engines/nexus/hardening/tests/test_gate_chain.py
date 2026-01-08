"""Targeted gate chain tests for PHASE 06."""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from engines.budget.models import BudgetPolicy
from engines.budget.repository import InMemoryBudgetPolicyRepository
from engines.common.identity import RequestContext
from engines.firearms.models import FirearmDecision
from engines.kill_switch.models import KillSwitchUpdate
from engines.kill_switch.repository import InMemoryKillSwitchRepository
from engines.kill_switch.service import KillSwitchService
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


class _AlwaysAllowFirearms:
    def require_licence_or_raise(self, *args, **kwargs):
        return None

    def check_access(self, *args, **kwargs):
        return SimpleNamespace(allowed=True, reason="pass", strategy_lock_required=False, required_license_types=[])


class _AlwaysAllowStrategyLock:
    def require_strategy_lock_or_raise(self, *args, **kwargs):
        return None


class _StubBudgetService:
    def __init__(self, total_cost: Decimal = Decimal("0")) -> None:
        self.total_cost = total_cost

    def summary(self, ctx, surface=None):
        return {"total_cost": self.total_cost, "total_events": 1, "grouped": {}}


class _StubKpiService:
    def list_corridors(self, ctx, surface):
        return [SimpleNamespace(kpi_name="kpi_demo", floor=None, ceiling=None)]

    def latest_raw_measurement(self, ctx, surface, kpi_name):
        return None


class _StubTemperatureService:
    def __init__(self, floors=None, ceilings=None):
        self._floors = floors or []
        self._ceilings = ceilings or []

    def compute_temperature(self, ctx, surface):
        return SimpleNamespace(floors_breached=self._floors, ceilings_breached=self._ceilings)


def _build_gate_chain(**overrides) -> GateChain:
    kill_service = overrides.get("kill_switch_service") or KillSwitchService(
        repo=InMemoryKillSwitchRepository()
    )
    policy_repo = overrides.get("budget_policy_repo")
    if policy_repo is None:
        policy_repo = InMemoryBudgetPolicyRepository()
        policy_repo.save_policy(
            BudgetPolicy(
                tenant_id="t_gate",
                env="dev",
                surface=None,
                mode="lab",
                app=None,
                threshold=Decimal("100"),
            )
        )
    return GateChain(
        kill_switch_service=kill_service,
        firearms_service=overrides.get("firearms_service") or _AlwaysAllowFirearms(),
        strategy_lock_service=overrides.get("strategy_lock_service") or _AlwaysAllowStrategyLock(),
        budget_service=overrides.get("budget_service") or _StubBudgetService(),
        kpi_service=overrides.get("kpi_service") or _StubKpiService(),
        temperature_service=overrides.get("temperature_service") or _StubTemperatureService(),
        budget_policy_repo=policy_repo,
        audit_logger=overrides.get("audit_logger") or (lambda *args, **kwargs: None),
    )


def test_kill_switch_blocks() -> None:
    repo = InMemoryKillSwitchRepository()
    kill_service = KillSwitchService(repo=repo)
    ctx = RequestContext(
        tenant_id="t_gate",
        env="dev",
        user_id="u_guard",
        mode="lab",
        surface_id="cards",
        app_id="card_app",
    )

    kill_service.upsert(ctx, KillSwitchUpdate(disabled_actions=["card_create"]))
    gate_chain = _build_gate_chain(kill_switch_service=kill_service)

    with pytest.raises(HTTPException) as exc:
        gate_chain.run(ctx, action="card_create", surface="cards", subject_type="card")
    assert exc.value.status_code == 403
    detail = exc.value.detail["error"]
    assert detail["code"] == "kill_switch.blocked"
    assert detail["gate"] == "kill_switch"
    assert detail["http_status"] == 403


def test_strategy_lock_requires_three_wise(monkeypatch) -> None:
    decision = SimpleNamespace(
        allowed=False,
        reason="strategy_lock_required",
        lock_id="lock-1",
        three_wise_verdict={"decision": "reject"},
    )
    monkeypatch.setattr(
        "engines.nexus.hardening.gate_chain.resolve_strategy_lock",
        lambda *args, **kwargs: decision,
    )

    gate_chain = _build_gate_chain()
    ctx = RequestContext(
        tenant_id="t_gate",
        env="dev",
        user_id="u_guard",
        mode="lab",
        surface_id="cards",
        app_id="card_app",
    )

    with pytest.raises(HTTPException) as exc:
        gate_chain.run(ctx, action="card_create", surface="cards", subject_type="card")
    detail = exc.value.detail["error"]
    assert exc.value.status_code == 403
    assert detail["code"] == "strategy_lock.approval_required"
    assert detail["gate"] == "strategy_lock"
    assert detail["http_status"] == 403


def test_temperature_breach_blocks() -> None:
    temp_stub = _StubTemperatureService(floors=["kpi1"], ceilings=[])
    gate_chain = _build_gate_chain(temperature_service=temp_stub)
    ctx = RequestContext(
        tenant_id="t_gate",
        env="dev",
        user_id="u_guard",
        mode="lab",
        surface_id="cards",
        app_id="card_app",
    )

    with pytest.raises(HTTPException) as exc:
        gate_chain.run(ctx, action="card_create", surface="cards", subject_type="card")
    assert exc.value.status_code == 403
    detail = exc.value.detail["error"]
    assert detail["code"] == "temperature_breach"
    assert detail["gate"] == "temperature"
    assert detail["http_status"] == 403


def test_firearms_blocks_dangerous_action() -> None:
    class _RejectFirearms:
        def check_access(self, *args, **kwargs):
            return FirearmDecision(
                allowed=False,
                reason="firearms.license_required",
                firearm_id="firearm.danger",
                required_license_types=["firearm.danger"],
            )

    gate_chain = _build_gate_chain(
        firearms_service=_RejectFirearms(),
    )
    ctx = RequestContext(
        tenant_id="t_gate",
        env="dev",
        user_id="u_guard",
        mode="lab",
        surface_id="cards",
        app_id="card_app",
    )

    with pytest.raises(HTTPException) as exc:
        gate_chain.run(ctx, action="dangerous_tool_use", surface="cards", subject_type="card")
    assert exc.value.status_code == 403
    detail = exc.value.detail["error"]
    assert detail["code"] == "firearms.license_required"
    assert detail["gate"] == "firearms"
    assert detail["http_status"] == 403


def test_gate_chain_emits_audit_with_request_metadata() -> None:
    captured: list[tuple[RequestContext, dict]] = []

    def audit_logger(ctx, *args, metadata=None, **kwargs):
        captured.append((ctx, metadata or {}))

    gate_chain = _build_gate_chain(audit_logger=audit_logger)
    ctx = RequestContext(
        tenant_id="t_gate",
        env="dev",
        user_id="u_guard",
        request_id="trace-999",
        mode="lab",
        surface_id="cards",
        app_id="card_app",
    )
    gate_chain.run(ctx, action="card_create", surface="cards", subject_type="card", subject_id="card-1")

    assert captured
    recorded_ctx, metadata = captured[0]
    assert recorded_ctx.request_id == "trace-999"
    assert metadata["subject_type"] == "card"
    assert metadata["subject_id"] == "card-1"


def test_gate_chain_blocks_when_budget_policy_missing() -> None:
    repo = InMemoryBudgetPolicyRepository()
    gate_chain = _build_gate_chain(
        budget_policy_repo=repo,
        budget_service=_StubBudgetService(),
    )
    ctx = RequestContext(
        tenant_id="t_gate",
        env="dev",
        user_id="u_guard",
        mode="lab",
        surface_id="cards",
        app_id="card_app",
    )

    with pytest.raises(HTTPException) as exc:
        gate_chain.run(ctx, action="card_create", surface="cards", subject_type="card")
    detail = exc.value.detail["error"]
    assert detail["code"] == "budget_threshold_missing"
    assert detail["gate"] == "budget"
    assert detail["http_status"] == 403


def test_gate_chain_blocks_when_budget_exceeded() -> None:
    repo = InMemoryBudgetPolicyRepository()
    repo.save_policy(
        BudgetPolicy(
            tenant_id="t_gate",
            env="dev",
            surface="cards",
            mode="lab",
            app="card_app",
            threshold=Decimal("1"),
        )
    )
    gate_chain = _build_gate_chain(
        budget_policy_repo=repo,
        budget_service=_StubBudgetService(total_cost=Decimal("2")),
    )
    ctx = RequestContext(
        tenant_id="t_gate",
        env="dev",
        user_id="u_guard",
        mode="lab",
        surface_id="cards",
        app_id="card_app",
    )

    with pytest.raises(HTTPException) as exc:
        gate_chain.run(ctx, action="card_create", surface="cards", subject_type="card")
    detail = exc.value.detail["error"]
    assert detail["code"] == "budget_threshold_exceeded"
    assert detail["gate"] == "budget"
    assert detail["http_status"] == 403
