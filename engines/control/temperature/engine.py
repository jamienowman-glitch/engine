"""Temperature engine with simple weighting model."""
from __future__ import annotations

from typing import Dict, List, Optional

from engines.control.state.schemas import BudgetCorridor, KpiCorridor, TemperatureState
from engines.control.temperature.schemas import TemperatureWeightsPlan

# Mutable weight store; replace via update_weighting_from_plan
WEIGHTS: Dict[str, float] = {
    "revenue_day": 1.5,
    "sessions": 1.0,
    "bounce_rate": -1.0,
}


def _score_kpi(kpi: KpiCorridor) -> float:
    if kpi.upper == kpi.lower:
        return 0.0
    midpoint = (kpi.upper + kpi.lower) / 2
    delta = midpoint - kpi.lower
    deviation = kpi.upper - midpoint
    return (deviation / max(delta, 1e-6)) * 10


def _aggregate(kpis: List[KpiCorridor]) -> float:
    score = 0.0
    for k in kpis:
        weight = WEIGHTS.get(k.name, 1.0)
        score += weight * _score_kpi(k)
    return score


def _band(score: float) -> str:
    if score <= -10:
        return "cold"
    if score >= 10:
        return "hot"
    return "sweet_spot"


def update_weighting_from_plan(plan: Dict[str, float]) -> None:
    WEIGHTS.update(plan)


def apply_plan(plan: Optional[TemperatureWeightsPlan]) -> None:
    if plan and plan.weights:
        update_weighting_from_plan(plan.weights)


def run(tenantId: str, env: str, kpis: List[KpiCorridor] | None = None, spend: List[BudgetCorridor] | None = None) -> TemperatureState:
    kpis = kpis or []
    band = _band(_aggregate(kpis))
    return TemperatureState(tenantId=tenantId, env=env, band=band, kpi_corridors=kpis, budget_corridors=spend or [])
