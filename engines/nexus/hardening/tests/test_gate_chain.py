"""Targeted gate chain tests for PHASE 06."""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from engines.common.identity import RequestContext
from engines.kill_switch.models import KillSwitchUpdate
from engines.kill_switch.repository import InMemoryKillSwitchRepository
from engines.kill_switch.service import KillSwitchService
from engines.nexus.hardening.gate_chain import GateChain


class _AlwaysAllowFirearms:
    def require_licence_or_raise(self, *args, **kwargs):
        return None


class _AlwaysAllowStrategyLock:
    def require_strategy_lock_or_raise(self, *args, **kwargs):
        return None


class _StubBudgetService:
    def summary(self, ctx, surface):
        return {"total_cost": Decimal("0"), "total_events": 1, "grouped": {}}


class _StubKpiService:
    def list_corridors(self, ctx, surface):
        return [object()]


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
    return GateChain(
        kill_switch_service=kill_service,
        firearms_service=overrides.get("firearms_service") or _AlwaysAllowFirearms(),
        strategy_lock_service=overrides.get("strategy_lock_service") or _AlwaysAllowStrategyLock(),
        budget_service=overrides.get("budget_service") or _StubBudgetService(),
        kpi_service=overrides.get("kpi_service") or _StubKpiService(),
        temperature_service=overrides.get("temperature_service") or _StubTemperatureService(),
        budget_threshold_resolver=overrides.get("budget_threshold_resolver", lambda surface: Decimal("100")),
        audit_logger=overrides.get("audit_logger") or (lambda *args, **kwargs: None),
    )


def test_kill_switch_blocks() -> None:
    repo = InMemoryKillSwitchRepository()
    kill_service = KillSwitchService(repo=repo)
    ctx = RequestContext(tenant_id="t_gate", env="dev", user_id="u_guard")

    kill_service.upsert(ctx, KillSwitchUpdate(disabled_actions=["card_create"]))
    gate_chain = _build_gate_chain(kill_switch_service=kill_service)

    with pytest.raises(HTTPException) as exc:
        gate_chain.run(ctx, action="card_create", surface="cards", subject_type="card")
    assert exc.value.status_code == 403
    assert exc.value.detail["error"] == "kill_switch_blocked"


def test_strategy_lock_requires_three_wise() -> None:
    class _RejectStrategyLock:
        def require_strategy_lock_or_raise(self, ctx, surface, action):
            raise HTTPException(status_code=409, detail={"error": "strategy_lock_required", "action": action})

    gate_chain = _build_gate_chain(strategy_lock_service=_RejectStrategyLock())
    ctx = RequestContext(tenant_id="t_gate", env="dev", user_id="u_guard")

    with pytest.raises(HTTPException) as exc:
        gate_chain.run(ctx, action="card_create", surface="cards", subject_type="card")
    assert exc.value.status_code == 409
    assert exc.value.detail["error"] == "strategy_lock_required"


def test_temperature_breach_blocks() -> None:
    temp_stub = _StubTemperatureService(floors=["kpi1"], ceilings=[])
    gate_chain = _build_gate_chain(temperature_service=temp_stub)
    ctx = RequestContext(tenant_id="t_gate", env="dev", user_id="u_guard")

    with pytest.raises(HTTPException) as exc:
        gate_chain.run(ctx, action="card_create", surface="cards", subject_type="card")
    assert exc.value.status_code == 403
    assert exc.value.detail["error"] == "temperature_breach"


def test_firearms_blocks_dangerous_action() -> None:
    class _RejectFirearms:
        def require_licence_or_raise(self, *args, **kwargs):
            raise HTTPException(status_code=403, detail={"error": "firearms_licence_required", "action": args[-1]})

    gate_chain = _build_gate_chain(
        firearms_service=_RejectFirearms(),
    )
    ctx = RequestContext(tenant_id="t_gate", env="dev", user_id="u_guard")

    with pytest.raises(HTTPException) as exc:
        gate_chain.run(ctx, action="dangerous_tool_use", surface="cards", subject_type="card")
    assert exc.value.status_code == 403
    assert exc.value.detail["error"] == "firearms_licence_required"


def test_gate_chain_emits_audit_with_request_metadata() -> None:
    captured: list[tuple[RequestContext, dict]] = []

    def audit_logger(ctx, *args, metadata=None, **kwargs):
        captured.append((ctx, metadata or {}))

    gate_chain = _build_gate_chain(audit_logger=audit_logger)
    ctx = RequestContext(tenant_id="t_gate", env="dev", user_id="u_guard", request_id="trace-999")
    gate_chain.run(ctx, action="card_create", surface="cards", subject_type="card", subject_id="card-1")

    assert captured
    recorded_ctx, metadata = captured[0]
    assert recorded_ctx.request_id == "trace-999"
    assert metadata["subject_type"] == "card"
    assert metadata["subject_id"] == "card-1"
