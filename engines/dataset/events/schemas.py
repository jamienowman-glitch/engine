"""Canonical DatasetEvent schema (N-01.B)."""
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator, root_validator

from engines.logging.events.contract import (
    DEFAULT_DATASET_SCHEMA_VERSION,
    EventSeverity,
    StorageClass,
    event_contract_enforced,
)


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
    mode: Optional[str] = None
    project_id: Optional[str] = None
    app_id: Optional[str] = None
    surface_id: Optional[str] = None
    run_id: Optional[str] = None
    step_id: Optional[str] = None
    schema_version: str = Field(default=DEFAULT_DATASET_SCHEMA_VERSION)
    severity: EventSeverity = Field(default=EventSeverity.INFO)
    storage_class: StorageClass = Field(default=StorageClass.OPS)

    @field_validator("mode", mode="before")
    def _default_mode(cls, value: Optional[str], values: dict[str, Any]) -> Optional[str]:
        if value:
            return value
        return values.get("env")

    @root_validator(skip_on_failure=True)
    def _require_scope_fields(cls, values: dict[str, Any]) -> dict[str, Any]:
        if not event_contract_enforced():
            return values
        missing = []
        for name in (
            "tenantId",
            "mode",
            "project_id",
            "requestId",
            "traceId",
            "run_id",
            "step_id",
            "schema_version",
            "severity",
            "storage_class",
        ):
            if not values.get(name):
                missing.append(name)
        if missing:
            raise ValueError(f"missing required scope fields: {', '.join(sorted(missing))}")
        return values
