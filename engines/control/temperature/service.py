from __future__ import annotations

from typing import List, Optional

from engines.control.state.schemas import BudgetCorridor, KpiCorridor
from engines.control.temperature.engine import apply_plan, run
from engines.control.temperature.schemas import TemperatureWeightsPlan
from engines.dataset.events.schemas import DatasetEvent
from engines.logging.events.engine import run as log_event
from engines.nexus.backends import get_backend
from engines.guardrails.strategy_lock import engine as strategy_lock
from engines.guardrails.strategy_lock.schemas import StrategyScope


def load_weights_from_nexus(tenantId: str, env: str) -> Optional[TemperatureWeightsPlan]:
    backend = get_backend()
    if not hasattr(backend, "get_latest_plan"):
        return None
    data = backend.get_latest_plan(kind="temperature", tenantId=tenantId, env=env, status="approved")
    if not data:
        return None
    try:
        return TemperatureWeightsPlan(**data)
    except Exception:
        return None


def measure_temperature(tenantId: str, env: str, kpis: List[KpiCorridor], budgets: List[BudgetCorridor]):
    plan = load_weights_from_nexus(tenantId, env)
    apply_plan(plan)
    state = run(tenantId, env, kpis=kpis, spend=budgets)
    event = DatasetEvent(
        tenantId=tenantId,
        env=env,
        surface="control",
        agentId="temperature-engine",
        input={"kpis": [k.dict() for k in kpis], "budgets": [b.dict() for b in budgets]},
        output={"band": state.band},
        metadata={"kind": "temperature_measurement"},
    )
    log_event(event)
    return state


def review_and_apply_temperature_plan(
    tenantId: str,
    env: str,
    weights: dict,
    proposed_by: str,
    note: str = "",
) -> TemperatureWeightsPlan:
    """Guarded planning path: run Strategy Lock then persist plan."""
    decision = strategy_lock.run(
        tenantId=tenantId,
        env=env,
        surface="control",
        conversationContext={},
        scope=StrategyScope(objective="temperature_plan_update", constraints=[note]),
    )
    if not decision.approved:
        raise RuntimeError("Strategy Lock rejected temperature plan")

    plan = TemperatureWeightsPlan(
        tenantId=tenantId,
        env=env,
        weights=weights,
        proposed_by=proposed_by,
        note=note,
        status="approved",
    )
    backend = get_backend()
    if hasattr(backend, "save_plan"):
        backend.save_plan("temperature", tenantId, plan.dict())
    return plan
