from __future__ import annotations

from typing import Any, Dict, Optional, Literal
from pydantic import BaseModel, Field

from engines.realtime.contracts import RoutingKeys

class CommandEnvelope(BaseModel):
    """
    Client sends this to propose a change.
    Strictly enforcing base_rev for optimistic concurrency.
    """
    id: str = Field(..., description="Client-side command ID for tracking")
    type: str = Field(..., description="Action type: update_node, create_edge, etc.")
    
    # Target resource
    canvas_id: str
    
    # State truth
    base_rev: int = Field(..., description="The revision this command is built upon")
    
    # Idempotency
    idempotency_key: str = Field(..., description="Unique key to prevent replay")
    
    # Payload
    args: Dict[str, Any] = Field(default_factory=dict)
    
    # Routing (explicit for validation)
    routing: Optional[RoutingKeys] = None 


class RevisionResult(BaseModel):
    """
    Server response to a command.
    """
    status: Literal["applied", "conflict", "rejected"]
    current_rev: int
    your_rev: Optional[int] = None # The rev assigned to this command if applied
    
    # If conflict, latest state or diff?
    # For MVP just signals mismatch.
    reason: Optional[str] = None
    
    # If applied, the event ID generated
    event_id: Optional[str] = None


class CanvasOp(BaseModel):
    """An atomic operation applied to a canvas."""
    id: str
    canvas_id: str
    type: str
    args: Dict[str, Any] = Field(default_factory=dict)
    author: Optional[str] = None
    timestamp: float = 0.0


class CanvasRevision(BaseModel):
    """Tracks the head revision of a canvas."""
    canvas_id: str
    head_rev: int = 0
    updated_at: float = 0.0


def _now() -> float:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).timestamp()
