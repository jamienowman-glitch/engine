from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class ScopeKPIBinding(BaseModel):
    # What KPI does this scope's usage impact?
    # e.g. "image_generation_count"
    metric_name: str
    impact_value: int = 1
    
class KPIBindingProfile(BaseModel):
    # Mapping: scope_identifier -> Binding
    scopes: Dict[str, ScopeKPIBinding] = Field(default_factory=dict)
