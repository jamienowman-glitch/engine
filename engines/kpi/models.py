from __future__ import annotations
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone

# --- Phase 2: Bindings ---
class ScopeKPIBinding(BaseModel):
    # What KPI does this scope's usage impact?
    # e.g. "image_generation_count"
    metric_name: str
    impact_value: int = 1
    
class KPIBindingProfile(BaseModel):
    # Mapping: scope_identifier -> Binding
    scopes: Dict[str, ScopeKPIBinding] = Field(default_factory=dict)


# --- Registry Metadata ---
class KpiCategory(BaseModel):
    id: Optional[str] = None
    tenant_id: str
    env: str
    name: str # e.g. "Performance"
    description: Optional[str] = None
    model_config = ConfigDict(extra="allow")

class KpiType(BaseModel):
    id: Optional[str] = None
    tenant_id: str
    env: str
    name: str # e.g. "Latency"
    description: Optional[str] = None
    category_id: Optional[str] = None # Link to Category
    model_config = ConfigDict(extra="allow")


# --- Legacy/Full KPI Models (Required for Service) ---
class KpiDefinition(BaseModel):
    id: Optional[str] = None
    tenant_id: str
    env: str
    surface: str
    name: str
    description: Optional[str] = None
    unit: str = "count"
    window_seconds: int = 86400  # Default 24h
    model_config = ConfigDict(extra="allow")

class KpiCorridor(BaseModel):
    id: Optional[str] = None
    tenant_id: str
    env: str
    surface: str
    kpi_name: str
    floor: Optional[float] = None
    ceiling: Optional[float] = None
    model_config = ConfigDict(extra="allow")

class KpiRawMeasurement(BaseModel):
    id: Optional[str] = None
    tenant_id: str
    env: str
    surface: str
    kpi_name: str
    value: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    meta: Dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(extra="allow")

class SurfaceKpiSet(BaseModel):
    id: Optional[str] = None
    tenant_id: str
    env: str
    surface: str
    kpis: List[str] = Field(default_factory=list)
    model_config = ConfigDict(extra="allow")
