from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Any
from pydantic import BaseModel, Field

def _now() -> datetime:
    return datetime.now(timezone.utc)

class AuditRequest(BaseModel):
    target_artifact_id: Optional[str] = None
    ruleset: Optional[str] = "standard"

class AuditFinding(BaseModel):
    severity: str # "info", "warning", "error"
    message: str
    location: Optional[str] = None

class AuditReport(BaseModel):
    id: str
    canvas_id: str
    findings: List[AuditFinding]
    score: float # 0.0 - 1.0
    created_at: datetime = Field(default_factory=_now)
    artifact_ref_id: Optional[str] = None # Link to stored JSON
