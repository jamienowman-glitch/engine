"""Creative evaluation and QPU metadata schemas."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

from pydantic import BaseModel, Field


class CreativeEval(BaseModel):
    id: str
    tenant_id: str = Field(..., pattern=r"^t_[a-z0-9_-]+$")
    artefact_ref: str
    backend: str  # imagen|nova|other
    scores: Dict[str, float] = Field(default_factory=dict)
    eval_payload_ref: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class QpuJobMetadata(BaseModel):
    job_id: str
    backend: str  # braket
    tenant_id: str = Field(..., pattern=r"^t_[a-z0-9_-]+$")
    episode_id: Optional[str] = None
    parameters_ref: Optional[str] = None
    results_ref: Optional[str] = None
    status: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
