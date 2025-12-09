import pytest
from pydantic import ValidationError

from engines.control.state.schemas import BudgetCorridor, KpiCorridor, TemperatureState


def test_temperature_state_validates_tenant() -> None:
    state = TemperatureState(tenantId="t_demo", env="dev")
    assert state.band == "neutral"


def test_temperature_state_rejects_bad_tenant() -> None:
    with pytest.raises(ValidationError):
        TemperatureState(tenantId="demo", env="dev")


def test_budget_corridor_fields() -> None:
    corridor = BudgetCorridor(name="default", spend_floor=0.0, spend_cap=100.0)
    assert corridor.spend_cap == 100.0


def test_kpi_corridor_fields() -> None:
    corridor = KpiCorridor(name="conv", lower=0.1, upper=0.5)
    assert corridor.lower < corridor.upper
