"""Temperature primitives: floors, ceilings, weights, snapshots."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class KpiMetricRef(BaseModel):
    key: str
    description: Optional[str] = None
    dimension: Literal["count", "rate", "currency", "duration", "other"] = "other"


class FloorConfig(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    tenant_id: str
    env: str
    surface: str
    performance_floors: Dict[str, float] = Field(default_factory=dict)
    cadence_floors: Dict[str, float] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class CeilingConfig(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    tenant_id: str
    env: str
    surface: str
    ceilings: Dict[str, float] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class TemperatureWeights(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    tenant_id: str
    env: str
    surface: str
    weights: Dict[str, float] = Field(default_factory=dict)
    source: Literal["system_default", "tenant_override", "llm_tuned"] = "system_default"
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class TemperatureSnapshot(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    tenant_id: str
    env: str
    surface: str
    value: float
    window_start: datetime
    window_end: datetime
    floors_breached: list[str] = Field(default_factory=list)
    ceilings_breached: list[str] = Field(default_factory=list)
    raw_metrics: Dict[str, float] = Field(default_factory=dict)
    source: str = "in_memory"
    usage_window_days: int = 7
    kpi_corridors_used: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)

    @staticmethod
    def default_window_end() -> datetime:
        return _now()

    @staticmethod
    def default_window_start(days: int = 7) -> datetime:
        return _now() - timedelta(days=days)
