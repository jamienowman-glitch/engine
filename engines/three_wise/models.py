from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ThreeWiseVerdict(str, Enum):
    approve = "APPROVE"
    reject = "REJECT"
    unsure = "UNSURE"


class Opinion(BaseModel):
    model_id: str
    content: str
    verdict: ThreeWiseVerdict = ThreeWiseVerdict.unsure


class ThreeWiseRecord(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    tenant_id: str
    env: str
    surface: Optional[str] = None
    question: str
    context: Optional[str] = None
    opinions: List[Opinion] = Field(default_factory=list)
    verdict: Optional[ThreeWiseVerdict] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
