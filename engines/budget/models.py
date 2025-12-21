from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class UsageEvent(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    tenant_id: str
    env: str
    surface: Optional[str] = None  # e.g., squared/cubed/os
    tool_type: Optional[str] = None  # llm/embedding/vector_search/etc
    tool_id: Optional[str] = None  # card/engine name
    provider: str
    model_or_plan_id: Optional[str] = None
    tokens_input: int = 0
    tokens_output: int = 0
    cost: Decimal = Decimal("0")
    currency: str = "USD"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)
