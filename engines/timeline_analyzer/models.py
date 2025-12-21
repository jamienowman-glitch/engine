from __future__ import annotations
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

HealthStatus = Literal["OK", "WARNING", "CRITICAL"]

class ComplexityMetric(BaseModel):
    name: str # e.g. "Overlap Density", "Total Duration"
    value: float
    threshold: Optional[float] = None
    status: HealthStatus = "OK"

class HealthReport(BaseModel):
    sequence_id: str
    overall_status: HealthStatus
    metrics: List[ComplexityMetric] = Field(default_factory=list)
    messages: List[str] = Field(default_factory=list) # e.g. "Too many tracks at 00:05"
