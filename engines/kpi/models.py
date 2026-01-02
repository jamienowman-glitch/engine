from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class KpiDefinition(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    tenant_id: str
    env: str
    surface: Optional[str] = None
    name: str
    description: Optional[str] = None
    unit: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class KpiCorridor(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    tenant_id: str
    env: str
    surface: Optional[str] = None
    kpi_name: str
    floor: Optional[float] = None
    ceiling: Optional[float] = None
    cadence_floor: Optional[float] = None
    cadence_ceiling: Optional[float] = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class SurfaceKpiEntry(BaseModel):
    name: str
    description: Optional[str] = None
    calculation: Optional[str] = None
    window_token: str
    comparison_token: Optional[str] = None
    estimate: bool = False
    missing_components: List[str] = Field(default_factory=list)
    display_label: Optional[str] = None
    notes: Optional[str] = None


class SurfaceKpiSet(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    tenant_id: str
    env: str
    surface: Optional[str] = None
    entries: List[SurfaceKpiEntry] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class KpiRawMeasurement(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    tenant_id: str
    env: str
    surface: Optional[str] = None
    kpi_name: str
    value: float
    app_id: Optional[str] = None
    project_id: Optional[str] = None
    run_id: Optional[str] = None
    trace_id: Optional[str] = None
    exact: bool = True
    missing_components: List[str] = Field(default_factory=list)
    source: str = "raw_ingestion"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)
