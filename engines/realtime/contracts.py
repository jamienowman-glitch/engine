"""Canonical Realtime Event Contracts (REALTIME_SPEC_V1)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, root_validator

from engines.logging.events.contract import (
    DEFAULT_STREAM_SCHEMA_VERSION,
    EventSeverity,
    StorageClass,
    event_contract_enforced,
)
# --- Routing Keys ---

class ActorType(str, Enum):
    HUMAN = "human"
    AGENT = "agent"
    SYSTEM = "system"


class RoutingKeys(BaseModel):
    """
    Mandatory routing keys for all StreamEvent envelopes.
    """
    tenant_id: str = Field(..., pattern=r"^t_[a-z0-9_-]+$")
    mode: Optional[str] = None
    env: Literal["dev", "staging", "prod", "stage"]
    # Hierarchy
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    app_id: Optional[str] = None
    # Surface
    surface_id: Optional[str] = None
    canvas_id: Optional[str] = None
    projection_id: Optional[str] = None
    panel_id: Optional[str] = None
    thread_id: Optional[str] = None
    # Actor
    actor_id: str
    actor_type: ActorType
    session_id: Optional[str] = None
    device_id: Optional[str] = None


# --- IDs ---

class EventIds(BaseModel):
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    run_id: Optional[str] = None
    step_id: Optional[str] = None


# --- Priority & Meta ---

class EventPriority(str, Enum):
    TRUTH = "truth"  # Authoritative commits
    GESTURE = "gesture"  # Ephemeral (mouse, typing)
    INFO = "info"  # Notifications/Chat


class PersistPolicy(str, Enum):
    ALWAYS = "always"
    SAMPLED = "sampled"
    NEVER = "never"


class EventMeta(BaseModel):
    schema_ver: Optional[str] = None
    priority: EventPriority = EventPriority.INFO
    persist: PersistPolicy = PersistPolicy.ALWAYS
    last_event_id: Optional[str] = None
    schema_version: str = Field(default=DEFAULT_STREAM_SCHEMA_VERSION)
    severity: EventSeverity = Field(default=EventSeverity.INFO)
    storage_class: StorageClass = Field(default=StorageClass.STREAM)


# --- Canonical StreamEvent ---

class StreamEvent(BaseModel):
    """
    The Single Source of Truth event envelope for Northstar Realtime.
    Matches REALTIME_SPEC_V1.
    """
    v: int = 1
    type: str  # e.g. "token_chunk", "canvas_commit", "presence_state"
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    seq: Optional[int] = None  # Monotonic sequence per stream key
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))  # Should be ULID ideally
    trace_id: Optional[str] = None
    span_id: Optional[str] = None

    ids: EventIds = Field(default_factory=EventIds)
    routing: RoutingKeys
    data: Dict[str, Any] = Field(default_factory=dict)
    meta: EventMeta = Field(default_factory=EventMeta)

    @root_validator(skip_on_failure=True)
    def _require_contract_fields(cls, values: dict[str, Any]) -> dict[str, Any]:
        if not event_contract_enforced():
            return values
        routing: RoutingKeys | None = values.get("routing")
        ids: EventIds | None = values.get("ids")
        meta: EventMeta | None = values.get("meta")
        missing = []
        if not routing or not routing.mode:
            missing.append("routing.mode")
        if not ids or not ids.request_id:
            missing.append("ids.request_id")
        if not ids or not ids.run_id:
            missing.append("ids.run_id")
        if not ids or not ids.step_id:
            missing.append("ids.step_id")
        if not values.get("trace_id"):
            missing.append("trace_id")
        if not meta or not meta.schema_version:
            missing.append("meta.schema_version")
        if not meta or not meta.severity:
            missing.append("meta.severity")
        if not meta or not meta.storage_class:
            missing.append("meta.storage_class")
        if missing:
            raise ValueError(f"missing required stream envelope fields: {', '.join(sorted(missing))}")
        return values

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# --- Legacy Adapter Helpers ---

def from_legacy_message(
    msg: Any,  # engines.chat.contracts.Message
    tenant_id: str,
    env: str,
    request_id: Optional[str] = None,
    trace_id: Optional[str] = None
) -> StreamEvent:
    """
    Convert a legacy Message object into a StreamEvent.
    """
    # Infer actor type
    actor_type = ActorType.HUMAN
    if msg.role == "agent" or msg.sender.id.startswith("agent-"):
        actor_type = ActorType.AGENT
    elif msg.role == "system":
        actor_type = ActorType.SYSTEM

    # Routing
    routing = RoutingKeys(
        tenant_id=tenant_id,
        env=env,  # type: ignore
        mode=env,
        thread_id=msg.thread_id,
        actor_id=msg.sender.id,
        actor_type=actor_type,
        # app/surface not reliably known in legacy Message scope unless parsed
        app_id=msg.scope.app if msg.scope else None,
        surface_id=msg.scope.surface if msg.scope else None
    )

    # Convert text payload
    # If text is stringified JSON, we might want to unwrap it if it matches known shapes,
    # but for now we put it in data.text or data.payload
    
    # Check if text contains an internal envelope (e.g. from core_bridge)
    import json
    data_payload = {"text": msg.text, "role": msg.role}
    event_type = "agent_message" if msg.role == "agent" else "user_message"

    try:
        # Try to detect if it's already an envelope (e.g. core_bridge emission)
        c = json.loads(msg.text)
        if isinstance(c, dict) and "type" in c and "data" in c:
            # It's a structured event from Core Bridge!
            event_type = c["type"]
            data_payload = c["data"]
            # Merge IDs if possible
            if "request_id" in c:
                request_id = c["request_id"]
    except Exception:
        pass

    event = StreamEvent(
        type=event_type,
        ts=msg.created_at,
        event_id=msg.id,
        ids=EventIds(request_id=request_id, run_id=request_id, step_id=msg.id),
        routing=routing,
        data=data_payload,
        meta=EventMeta(
            priority=EventPriority.INFO,
            persist=PersistPolicy.ALWAYS
        )
    )
    event.trace_id = trace_id
    event.meta.last_event_id = event.event_id
    return event
