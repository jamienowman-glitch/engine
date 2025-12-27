"""Core identity and tenant models (phase 1 backbone)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    password_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class Tenant(BaseModel):
    id: str
    name: str
    slug: Optional[str] = None
    status: Literal["active", "disabled", "suspended"] = "active"
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class TenantMembership(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    tenant_id: str
    user_id: str
    role: Literal["owner", "admin", "member", "viewer"] = "member"
    status: Literal["active", "pending", "revoked"] = "active"
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class TenantKeyConfig(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    tenant_id: str
    env: str
    slot: str
    provider: str
    secret_name: str
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

    @field_validator("metadata", mode="before")
    @classmethod
    def _metadata_dict(cls, v):
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise TypeError("metadata must be a dict")
        return {str(k): v for k, v in v.items()}


class TenantAnalyticsConfig(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    tenant_id: str
    env: str
    surface: str
    ga4_measurement_id: Optional[str] = None
    ga4_api_secret_slot: Optional[str] = None
    meta_pixel_id: Optional[str] = None
    tiktok_pixel_id: Optional[str] = None
    snap_pixel_id: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

class TenantMode(BaseModel):
    """Control-plane record for tenant operational mode (enterprise/saas/lab).
    
    Modes are persisted records owned by t_system; they are metadata
    that can be attached to tenants to indicate deployment/operational context.
    No behavior changes in Phase 0; mode is read-only metadata.
    """
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str  # e.g. "enterprise", "saas", "lab"
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class Surface(BaseModel):
    """Control-plane record for a Surface (content container/workspace).
    
    Surfaces are first-class control-plane primitives tied to a tenant.
    They represent a named content space (e.g. "default", "staging").
    """
    id: str = Field(default_factory=lambda: f"s_{uuid4().hex}")
    tenant_id: str  # Surfaces are tenant-scoped
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    status: Literal["active", "archived", "deleted"] = "active"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class App(BaseModel):
    """Control-plane record for an App (application/deployment unit).
    
    Apps are first-class control-plane primitives tied to a tenant.
    They represent a deployable application or service.
    """
    id: str = Field(default_factory=lambda: f"a_{uuid4().hex}")
    tenant_id: str  # Apps are tenant-scoped
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    app_type: Literal["web", "mobile", "api", "backend"] = "web"
    status: Literal["active", "archived", "deleted"] = "active"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class ControlPlaneProject(BaseModel):
    """Control-plane record for a Project (canonical project registry).
    
    Projects are durable records keyed by (tenant_id, env, project_id).
    This is separate from video_timeline's project domain; it's a canonical
    "project exists" registry for cross-service routing and entitlements.
    """
    id: str = Field(default_factory=lambda: uuid4().hex)
    tenant_id: str
    env: str
    project_id: str  # The value used in X-Project-Id header
    name: Optional[str] = None
    description: Optional[str] = None
    status: Literal["active", "archived", "deleted"] = "active"
    default_surface_id: Optional[str] = None
    default_app_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)