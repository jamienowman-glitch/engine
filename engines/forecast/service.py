"""Forecast service and anomaly detection stubs."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List

from engines.forecast.schemas import ForecastJob, ForecastSeries


class ForecastBackend:
    """Protocol-like stub for forecast backends."""

    def create_job(self, series: ForecastSeries, horizon: str) -> Dict[str, Any]:
        raise NotImplementedError

    def get_forecast(self, backend_job_id: str) -> Dict[str, Any]:
        raise NotImplementedError


class ForecastService:
    def __init__(self, backend: ForecastBackend):
        self._backend = backend
        self._jobs: Dict[str, ForecastJob] = {}

    def create_forecast_job(self, series: ForecastSeries, horizon: str, backend_name: str) -> ForecastJob:
        backend_job = self._backend.create_job(series, horizon)
        job_id = str(uuid.uuid4())
        job = ForecastJob(
            job_id=job_id,
            backend=backend_name,
            status="scheduled",
            horizon=horizon,
            series_id=series.series_id,
        )
        self._jobs[job_id] = job
        return job

    def get_forecast(self, job_id: str) -> Dict[str, Any]:
        job = self._jobs.get(job_id)
        if not job:
            raise KeyError(job_id)
        backend_result = self._backend.get_forecast(job_id)
        job.status = "completed"
        self._jobs[job_id] = job
        return backend_result

    def compare_actual_vs_forecast(self, series_id: str, actual: List[float], forecast: List[float]) -> Dict[str, Any]:
        deltas = []
        for a, f in zip(actual, forecast):
            deltas.append(a - f)
        anomalies = [i for i, d in enumerate(deltas) if abs(d) > 0.2 * (abs(forecast[i]) + 1e-6)]
        return {"deltas": deltas, "anomalies": anomalies}
