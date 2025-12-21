"""Canonical DatasetEvent schema (N-01.B)."""
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class DatasetEvent(BaseModel):
    tenantId: str = Field(..., pattern=r"^t_[a-z0-9_-]+$")
    env: str
    surface: str
    agentId: str
    input: Dict[str, Any]
    output: Dict[str, Any]
    pii_flags: Dict[str, Any] = Field(default_factory=dict)
    train_ok: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_term: Optional[str] = None
    utm_content: Optional[str] = None
    seo_slug: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    asset_alt_text: Optional[str] = None
    analytics_event_type: Optional[str] = None
    analytics_platform: Optional[str] = None
    traceId: Optional[str] = None
    requestId: Optional[str] = None
    actorType: Optional[str] = None
