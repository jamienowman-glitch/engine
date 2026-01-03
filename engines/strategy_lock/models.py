from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class StrategyScope(str, Enum):
    campaign = "campaign"
    budget = "budget"
    kpi_corridor = "kpi_corridor"
    code_deploy = "code_deploy"
    app_toggle = "app_toggle"
    other = "other"


# Reserved action names for builder/seo
ACTION_BUILDER_PUBLISH_PAGE = "builder:publish_page"
ACTION_BUILDER_UPDATE_PAGE = "builder:update_page"
ACTION_BUILDER_UPDATE_GLOBAL_SEO = "builder:update_global_seo"
ACTION_SEO_PAGE_CONFIG_UPDATE = "seo_page_config_update"
ACTION_VECTOR_INGEST = "vector:ingest"
ACTION_KILL_SWITCH_UPDATE = "safety:kill_switch_update"


class StrategyStatus(str, Enum):
    draft = "draft"
    approved = "approved"
    rejected = "rejected"
    expired = "expired"


class StrategyLock(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    tenant_id: str
    env: str
    mode: Optional[str] = None
    project_id: Optional[str] = None
    surface: Optional[str] = None
    scope: StrategyScope
    title: str
    description: Optional[str] = None
    constraints: Dict[str, Any] = Field(default_factory=dict)
    allowed_actions: List[str] = Field(default_factory=list)
    three_wise_id: Optional[str] = None
    created_by_user_id: str
    approved_by_user_id: Optional[str] = None
    status: StrategyStatus = StrategyStatus.draft
    valid_from: datetime = Field(default_factory=_now)
    valid_until: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    version: int = 1
    deleted: bool = False


class StrategyLockCreate(BaseModel):
    surface: Optional[str] = None
    scope: StrategyScope
    title: str
    description: Optional[str] = None
    constraints: Dict[str, Any] = Field(default_factory=dict)
    allowed_actions: List[str] = Field(default_factory=list)
    three_wise_id: Optional[str] = None
    valid_from: datetime = Field(default_factory=_now)
    valid_until: Optional[datetime] = None


class StrategyLockUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    constraints: Optional[Dict[str, Any]] = None
    allowed_actions: Optional[List[str]] = None
    three_wise_id: Optional[str] = None
    valid_until: Optional[datetime] = None


class StrategyDecision(BaseModel):
    allowed: bool
    reason: Optional[str] = None
    lock_id: Optional[str] = None
    three_wise_verdict: Optional[str] = None
