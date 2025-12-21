from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field

def _now() -> datetime:
    return datetime.now(timezone.utc)

class ArtifactRef(BaseModel):
    id: str
    canvas_id: str
    size: int
    mime_type: str
    url: str # Pre-signed or public URL
    created_at: datetime = Field(default_factory=_now)
    created_by: str # user_id
    key: Optional[str] = None # Storage key/path
