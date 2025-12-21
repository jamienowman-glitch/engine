from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, Field


class TemperatureWeightsPlan(BaseModel):
    tenantId: str = Field(..., pattern=r"^t_[a-z0-9_-]+$")
    env: str
    weights: Dict[str, float] = Field(default_factory=dict)
    note: Optional[str] = None
    proposed_by: Optional[str] = None
    status: str = Field(default="approved")
    version: int = 1
