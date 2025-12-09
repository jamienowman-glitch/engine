from __future__ import annotations

from engines.control.state.schemas import BudgetCorridor, KpiCorridor
from engines.control.temperature.service import measure_temperature
from engines.control.temperature.schemas import TemperatureWeightsPlan
from engines.nexus.backends import get_backend


class DummyBackend:
    def __init__(self):
        self._plans = {
            ("temperature", "t_demo", "dev"): {
                "tenantId": "t_demo",
                "env": "dev",
                "weights": {"conv": 5.0},
                "note": "boost conv",
                "version": 2,
            }
        }

    def get_latest_plan(self, kind, tenantId, env=None):
        return self._plans.get((kind, tenantId, env))


def test_measure_temperature_with_plan(monkeypatch):
    # Patch backend getter
    monkeypatch.setattr("engines.control.temperature.service.get_backend", lambda: DummyBackend())
    state = measure_temperature(
        "t_demo",
        "dev",
        kpis=[KpiCorridor(name="conv", lower=0.1, upper=0.5)],
        budgets=[BudgetCorridor(name="ad_spend", spend_floor=0, spend_cap=1000)],
    )
    assert state.tenantId == "t_demo"
    assert state.env == "dev"
    assert state.band in {"cold", "sweet_spot", "hot"}
