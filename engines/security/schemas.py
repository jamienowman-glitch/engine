"""Security finding and scan schemas."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class SecurityFinding(BaseModel):
    id: str
    tenant_id: str = Field(..., pattern=r"^t_[a-z0-9_-]+$")
    source: str  # ghas|dependabot|semgrep|sonar
    severity: str
    location: str
    description: str
    cwe: Optional[str] = None
    status: str = "open"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SecurityScanRun(BaseModel):
    run_id: str
    source: str
    repo_ref: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    findings_ref: Optional[str] = None
    status: str = "completed"
