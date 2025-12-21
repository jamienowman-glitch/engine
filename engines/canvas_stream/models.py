from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, Literal
from pydantic import BaseModel, Field

def _now() -> datetime:
    return datetime.now(timezone.utc)

class GestureEvent(BaseModel):
    kind: str # caret, selection, drag, etc.
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=_now)
    actor_id: str
