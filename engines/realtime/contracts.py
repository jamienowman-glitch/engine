"""Canonical Realtime Event Contracts (REALTIME_SPEC_V1)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

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
        ids=EventIds(request_id=request_id),
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
