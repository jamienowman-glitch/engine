"""Control-plane state schemas (T-01.A)."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class KpiCorridor(BaseModel):
    name: str
    lower: float
    upper: float


class BudgetCorridor(BaseModel):
    name: str
    spend_floor: float
    spend_cap: float


class TemperatureState(BaseModel):
    tenantId: str = Field(..., pattern=r"^t_[a-z0-9_-]+$")
    env: str
    band: str = "neutral"
    kpi_corridors: List[KpiCorridor] = Field(default_factory=list)
    budget_corridors: List[BudgetCorridor] = Field(default_factory=list)
