"""Forecast schemas."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

from pydantic import BaseModel, Field


class ForecastSeries(BaseModel):
    series_id: str
    metric_type: str  # tokens|spend|KPI|revenue|etc.
    tenant_id: str = Field(..., pattern=r"^t_[a-z0-9_-]+$")
    scope: str  # e.g., app/agent/model
    cadence: str  # daily/weekly/monthly
    history_ref: str
    metadata: Dict[str, str] = Field(default_factory=dict)


class ForecastJob(BaseModel):
    job_id: str
    backend: str  # vertex|bq_ml|aws_forecast
    status: str
    horizon: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    series_id: str
    confidence_intervals: Dict[str, float] = Field(default_factory=dict)
    results_ref: Optional[str] = None
