from __future__ import annotations

from engines.forecast.schemas import ForecastSeries
from engines.forecast.service import ForecastService


class DummyBackend:
    def __init__(self):
        self.jobs = []
        self.fetches = []

    def create_job(self, series: ForecastSeries, horizon: str):
        self.jobs.append((series.series_id, horizon))
        return {"backend_job_id": "b1"}

    def get_forecast(self, backend_job_id: str):
        self.fetches.append(backend_job_id)
        return {"values": [1.0, 2.0, 3.0]}


def test_create_and_get_forecast():
    backend = DummyBackend()
    svc = ForecastService(backend=backend)
    series = ForecastSeries(
        series_id="s1",
        metric_type="tokens",
        tenant_id="t_demo",
        scope="chat",
        cadence="daily",
        history_ref="bq://table",
    )
    job = svc.create_forecast_job(series, horizon="7d", backend_name="vertex")
    assert job.series_id == "s1"
    result = svc.get_forecast(job.job_id)
    assert result["values"][0] == 1.0


def test_compare_actual_vs_forecast_flags_anomalies():
    backend = DummyBackend()
    svc = ForecastService(backend=backend)
    compare = svc.compare_actual_vs_forecast("s1", actual=[10, 2], forecast=[5, 2])
    assert compare["anomalies"] == [0]
