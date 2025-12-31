from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import uuid4

from engines.common.identity import VALID_TENANT_PATTERN
from engines.logging.events.contract import (
    DEFAULT_DATASET_SCHEMA_VERSION,
    EventSeverity,
    StorageClass,
)
from pydantic import BaseModel, Field, root_validator


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
    mode: Optional[str] = None
    project_id: Optional[str] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    run_id: Optional[str] = None
    step_id: Optional[str] = None
    tokens_input: int = 0
    tokens_output: int = 0
    cost: Decimal = Decimal("0")
    currency: str = "USD"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)
    schema_version: str = DEFAULT_DATASET_SCHEMA_VERSION
    severity: EventSeverity = EventSeverity.INFO
    storage_class: StorageClass = StorageClass.COST

    @root_validator(skip_on_failure=True)
    def enforce_cost_storage_class(cls, values: dict[str, Any]) -> dict[str, Any]:
        storage = values.get("storage_class")
        if storage != StorageClass.COST:
            raise ValueError("UsageEvent storage_class must be 'cost'")
        return values


class BudgetPolicy(BaseModel):
    tenant_id: str
    env: str
    surface: Optional[str] = None
    mode: str
    app: Optional[str] = None
    threshold: Decimal = Field(..., ge=Decimal("0"))
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

    @root_validator(pre=True)
    def normalize_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        tenant = values.get("tenant_id")
        if not tenant:
            raise ValueError("tenant_id is required")
        if not VALID_TENANT_PATTERN.match(tenant):
            raise ValueError("tenant_id must match pattern ^t_[a-z0-9_-]+$")
        env_value = values.get("env")
        if not env_value:
            raise ValueError("env is required")
        values["env"] = env_value.lower()
        mode_value = values.get("mode")
        if not mode_value:
            raise ValueError("mode is required")
        values["mode"] = mode_value.lower()
        return values
