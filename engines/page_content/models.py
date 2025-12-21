from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PageContent(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    page_id: str = Field(default_factory=lambda: uuid4().hex)
    tenant_id: str
    env: str
    surface: Optional[str] = None
    slug: str
    html_or_json: str
    published: bool = False
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    published_at: Optional[datetime] = None
