from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import uuid4
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class BaseAnalyticsEvent(BaseModel):
    surface: str
    page_type: Optional[str] = None
    url: Optional[str] = None
    referrer: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_term: Optional[str] = None
    utm_content: Optional[str] = None
    seo_slug: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    metadata: Dict[str, Any] = {}


class PageViewEvent(BaseAnalyticsEvent):
    pass


class CtaClickEvent(BaseAnalyticsEvent):
    cta_id: Optional[str] = None
    label: Optional[str] = None


class AnalyticsEventRecord(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    tenant_id: str
    env: str
    event_type: str
    payload: Dict[str, Any]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
