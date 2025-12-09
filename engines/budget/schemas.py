"""Usage and cost schemas for budget watcher."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

from pydantic import BaseModel, Field


class UsageMetric(BaseModel):
    tenant_id: str = Field(..., pattern=r"^t_[a-z0-9_-]+$")
    vendor: str
    model: str
    surface: Optional[str] = None
    app: Optional[str] = None
    agent_id: Optional[str] = None
    tokens: Optional[int] = None
    calls: Optional[int] = None
    cost_estimate: Optional[float] = None
    timeframe: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, str] = Field(default_factory=dict)


class CostRecord(BaseModel):
    tenant_id: str = Field(..., pattern=r"^t_[a-z0-9_-]+$")
    vendor: str
    service: str
    cost: float
    period: str
    source_ref: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
