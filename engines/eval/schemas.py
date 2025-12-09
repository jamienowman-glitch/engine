"""Eval schemas."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EvalStatus(str):
    scheduled = "scheduled"
    running = "running"
    completed = "completed"
    failed = "failed"


class EvalJob(BaseModel):
    job_id: str
    tenant_id: str = Field(..., pattern=r"^t_[a-z0-9_-]+$")
    episode_id: Optional[str] = None
    eval_kind: str
    backend: str  # vertex|bedrock|ragas
    status: str = EvalStatus.scheduled
    scores: Dict[str, Any] = Field(default_factory=dict)
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
    model_call_ids: List[str] = Field(default_factory=list)
    prompt_snapshot_refs: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
