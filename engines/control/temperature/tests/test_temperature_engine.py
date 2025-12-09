from engines.control.state.schemas import KpiCorridor
from engines.control.temperature.engine import run, update_weighting_from_plan


def test_temperature_engine_stub() -> None:
    update_weighting_from_plan({"conv": 1.0})
    state = run("t_demo", "dev", kpis=[KpiCorridor(name="conv", lower=0.1, upper=0.5)])
    assert state.band in {"cold", "sweet_spot", "hot"}
    assert state.kpi_corridors[0].name == "conv"
