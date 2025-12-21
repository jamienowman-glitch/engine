from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class LicenceLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class LicenceStatus(str, Enum):
    active = "active"
    revoked = "revoked"
    expired = "expired"


class FirearmsLicence(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    tenant_id: str
    env: str
    subject_type: str  # agent|tool|surface|app
    subject_id: str
    scope: Optional[str] = None
    level: LicenceLevel = LicenceLevel.low
    status: LicenceStatus = LicenceStatus.active
    issued_by: Optional[str] = None
    issued_at: datetime = Field(default_factory=_now)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
