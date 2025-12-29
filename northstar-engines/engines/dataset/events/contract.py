"""
Event envelope & contract for Northstar Engines (Gate 1).

Canonical envelope schema for all events (DatasetEvent, StreamEvent, AuditEvent).
Enforces mode (saas|enterprise|lab), required scope fields, and schema versioning.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime
import uuid


class Mode(str, Enum):
    """Valid mode values (must match RequestContext.VALID_MODES)."""
    SAAS = "saas"
    ENTERPRISE = "enterprise"
    LAB = "lab"


class StorageClass(str, Enum):
    """Event storage classification for routing/retention."""
    DATASET = "dataset"         # Training data events
    REALTIME = "realtime"       # Live stream events
    AUDIT = "audit"             # Immutable audit trail
    COST = "cost"               # Usage & billing events
    METRIC = "metric"           # Observability & metrics


class EventSeverity(str, Enum):
    """Event severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class EventEnvelope:
    """
    Canonical event envelope (minimum required fields for all events).
    
    All events MUST include these fields. Gate 1 requires:
    - tenant_id: tenant scope (from RequestContext)
    - mode: deployment mode (from RequestContext, must be saas|enterprise|lab)
    - project_id: project scope (from RequestContext)
    - request_id: correlation ID (from RequestContext)
    - trace_id: distributed trace ID
    - event_id: unique event ID (auto-generated)
    - timestamp: event creation time
    - storage_class: event routing/retention classification
    
    Gate 1 optional (future enforce):
    - app_id, surface_id, run_id, step_id: scoping fields
    - schema_version: event schema version
    - severity: event severity level
    - actor_id: who/what triggered event
    - metadata: event-specific data
    """
    
    # === REQUIRED (Gate 1) ===
    tenant_id: str                           # ^t_[a-z0-9_-]+$
    mode: Mode                               # saas|enterprise|lab ONLY
    project_id: str                          # project scope
    request_id: str                          # from RequestContext
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    storage_class: StorageClass = StorageClass.DATASET
    
    # === OPTIONAL (Gate 1, future enforce) ===
    app_id: Optional[str] = None             # which app
    surface_id: Optional[str] = None         # which surface
    run_id: Optional[str] = None             # which run
    step_id: Optional[str] = None            # which step in run
    schema_version: str = "1.0"              # event schema version
    severity: EventSeverity = EventSeverity.INFO
    actor_id: Optional[str] = None           # who triggered
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate envelope on creation."""
        self._validate()
    
    def _validate(self):
        """Strict validation of required fields."""
        # Validate tenant_id
        if not self.tenant_id:
            raise ValueError("tenant_id is required in event envelope")
        if not self.tenant_id.startswith("t_"):
            raise ValueError(f"tenant_id must start with t_, got: {self.tenant_id}")
        
        # Validate mode
        if not self.mode:
            raise ValueError("mode is required in event envelope")
        if isinstance(self.mode, str):
            try:
                self.mode = Mode(self.mode)
            except ValueError:
                raise ValueError(
                    f"mode must be one of {[m.value for m in Mode]}, got: {self.mode}"
                )
        
        # Validate project_id
        if not self.project_id:
            raise ValueError("project_id is required in event envelope")
        
        # Validate request_id
        if not self.request_id:
            raise ValueError("request_id is required in event envelope")
        
        # Validate trace_id
        if not self.trace_id:
            raise ValueError("trace_id is required in event envelope")
        
        # Validate storage_class
        if isinstance(self.storage_class, str):
            try:
                self.storage_class = StorageClass(self.storage_class)
            except ValueError:
                raise ValueError(
                    f"storage_class must be one of {[s.value for s in StorageClass]}, "
                    f"got: {self.storage_class}"
                )
        
        # Validate severity
        if isinstance(self.severity, str):
            try:
                self.severity = EventSeverity(self.severity)
            except ValueError:
                raise ValueError(
                    f"severity must be one of {[s.value for s in EventSeverity]}, "
                    f"got: {self.severity}"
                )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert envelope to dict (for JSON serialization)."""
        return {
            "tenant_id": self.tenant_id,
            "mode": self.mode.value if isinstance(self.mode, Mode) else self.mode,
            "project_id": self.project_id,
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "storage_class": self.storage_class.value if isinstance(self.storage_class, StorageClass) else self.storage_class,
            "app_id": self.app_id,
            "surface_id": self.surface_id,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "schema_version": self.schema_version,
            "severity": self.severity.value if isinstance(self.severity, EventSeverity) else self.severity,
            "actor_id": self.actor_id,
            "metadata": self.metadata,
        }


@dataclass
class DatasetEvent:
    """
    Dataset training/validation event with envelope.
    
    Gate 1: Uses EventEnvelope for all required scope fields.
    """
    
    envelope: EventEnvelope
    
    # Event-specific fields
    event_type: str                          # e.g., "input", "output", "feedback"
    agent_id: Optional[str] = None           # which agent
    input_text: Optional[str] = None         # user/system input
    output_text: Optional[str] = None        # model output
    pii_flags: Dict[str, bool] = field(default_factory=dict)  # detected PII types
    train_ok: bool = True                    # safe for training
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate event on creation."""
        if not isinstance(self.envelope, EventEnvelope):
            raise TypeError("envelope must be EventEnvelope instance")
        self.envelope._validate()  # Re-validate envelope
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            **self.envelope.to_dict(),
            "event_type": self.event_type,
            "agent_id": self.agent_id,
            "input_text": self.input_text,
            "output_text": self.output_text,
            "pii_flags": self.pii_flags,
            "train_ok": self.train_ok,
            "additional_data": self.additional_data,
        }


@dataclass
class StreamEvent:
    """
    Realtime stream event with envelope.
    
    Gate 1: Uses EventEnvelope for scope fields.
    StreamEvent is consumed by UI and transports (SSE/WS).
    """
    
    envelope: EventEnvelope
    
    # Stream-specific fields
    event_type: str                          # e.g., "start", "chunk", "end"
    content: Optional[str] = None            # event content
    is_error: bool = False                   # error flag
    persist: bool = False                    # persist to storage
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate event on creation."""
        if not isinstance(self.envelope, EventEnvelope):
            raise TypeError("envelope must be EventEnvelope instance")
        self.envelope._validate()  # Re-validate envelope
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization (for transports)."""
        return {
            **self.envelope.to_dict(),
            "event_type": self.event_type,
            "content": self.content,
            "is_error": self.is_error,
            "persist": self.persist,
            "additional_data": self.additional_data,
        }


def build_envelope_from_context(
    ctx: "RequestContext",  # type: ignore
    storage_class: StorageClass = StorageClass.DATASET,
    trace_id: Optional[str] = None,
    app_id: Optional[str] = None,
    surface_id: Optional[str] = None,
    run_id: Optional[str] = None,
    step_id: Optional[str] = None,
) -> EventEnvelope:
    """
    Build EventEnvelope from RequestContext (common pattern).
    
    Args:
        ctx: RequestContext instance
        storage_class: event classification
        trace_id: optional trace ID (auto-generated if missing)
        app_id: optional app scope (from ctx if present)
        surface_id: optional surface scope (from ctx if present)
        run_id: optional run scope
        step_id: optional step scope
    
    Returns:
        EventEnvelope with all required fields populated from ctx
    """
    return EventEnvelope(
        tenant_id=ctx.tenant_id,
        mode=Mode(ctx.mode) if isinstance(ctx.mode, str) else ctx.mode,
        project_id=ctx.project_id,
        request_id=ctx.request_id,
        trace_id=trace_id or str(uuid.uuid4()),
        storage_class=storage_class,
        app_id=app_id or ctx.app_id,
        surface_id=surface_id or ctx.surface_id,
        run_id=run_id,
        step_id=step_id,
        actor_id=ctx.actor_id or ctx.user_id,
    )
