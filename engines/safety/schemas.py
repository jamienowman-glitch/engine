"""Safety context and verdict schemas."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SafetyContext(BaseModel):
    tenant_id: str = Field(..., pattern=r"^t_[a-z0-9_-]+$")
    actor: Optional[str] = None
    licences: List[str] = Field(default_factory=list)
    kpi_snapshot: Dict[str, Any] = Field(default_factory=dict)
    budget_snapshot: Dict[str, Any] = Field(default_factory=dict)
    tools: List[str] = Field(default_factory=list)
    nexus_refs: Dict[str, Any] = Field(default_factory=dict)
    agent_id: Optional[str] = None
    episode_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GuardrailVerdict(BaseModel):
    vendor_verdict: Optional[str] = None
    firearms_verdict: Optional[str] = None
    three_wise_verdict: Optional[str] = None
    result: str  # pass|soft_warn|hard_block
    reasons: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tenant_id: Optional[str] = None
    agent_id: Optional[str] = None
    episode_id: Optional[str] = None
