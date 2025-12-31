"""Service for handling canvas commands with strict concurrency control."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Dict, Optional, List, Set

from fastapi import HTTPException

from engines.canvas_commands.models import CommandEnvelope, RevisionResult
from engines.chat.contracts import Contact, Message
from engines.chat.service.transport_layer import bus, publish_message
from engines.common.identity import RequestContext
from engines.nexus.hardening.gate_chain import get_gate_chain
from engines.realtime.isolation import register_canvas_resource, verify_canvas_access

logger = logging.getLogger(__name__)

# --- In-Memory Truth Store (Phase 1-3 Stub) ---
# In production this is Postgres/Nexus
class CanvasState:
    def __init__(self, rev: int = 0):
        self.rev = rev
        self.applied_commands: Set[str] = set() # idempotency keys

class CommandRepository:
    def __init__(self):
        self._states: Dict[str, CanvasState] = {}
        # Pre-seed for testing
        self._states["canvas-1"] = CanvasState(rev=10)

    def get_state(self, canvas_id: str) -> CanvasState:
        if canvas_id not in self._states:
            self._states[canvas_id] = CanvasState(rev=0)
        return self._states[canvas_id]

repo = CommandRepository()


async def apply_command(
    tenant_id: str,
    user_id: str,
    command: CommandEnvelope,
    context: Optional[RequestContext] = None,
) -> RevisionResult:
    """
    Apply a command to a canvas strictly checking base_rev.
    """
    effective_tenant = context.tenant_id if context else tenant_id
    if context:
        register_canvas_resource(effective_tenant, command.canvas_id)

    # 1. Isolation Check
    verify_canvas_access(effective_tenant, command.canvas_id)

    if context:
        gate_chain = get_gate_chain()
        gate_chain.run(
            ctx=context,
            action="canvas_command",
            surface=context.surface_id or "canvas",
            subject_type="canvas",
            subject_id=command.canvas_id,
        )
    
    state = repo.get_state(command.canvas_id)
    
    # 2. Idempotency Check
    if command.idempotency_key in state.applied_commands:
        logger.info(f"Command {command.id} replay detected (idempotent)")
        return RevisionResult(
            status="applied",
            current_rev=state.rev,
            reason="Idempotent replay"
        )

    # 3. Revision Check (Optimistic Locking)
    if command.base_rev != state.rev:
        logger.warning(
            f"Conflict on {command.canvas_id}: client_base={command.base_rev} server={state.rev}"
        )
        return RevisionResult(
            status="conflict",
            current_rev=state.rev,
            reason=f"Revision Mismatch: Expected {state.rev}, got {command.base_rev}"
        )

    # 4. Apply (Stub Logic)
    # In real logic, we'd validate the transition.
    # Here we just accept and increment.
    state.rev += 1
    state.applied_commands.add(command.idempotency_key)
    
    new_rev = state.rev
    
    # 5. Emit Event (Truth)
    final_payload = {
        "kind": "canvas_commit",
        "cmd_id": command.id,
        "type": command.type,
        "rev": new_rev,
        "args": command.args
    }
    event_id: Optional[str] = None
    if context:
        msg = publish_message(
            command.canvas_id,
            Contact(id=user_id),
            json.dumps(final_payload),
            role="system",
            context=context,
        )
        event_id = msg.id
    else:
        msg = Message(
            id=command.id,
            thread_id=command.canvas_id, # Bus topic
            sender=Contact(id=user_id),
            text=json.dumps(final_payload),
            role="system",
            created_at=datetime.utcnow()
        )
        bus.add_message(command.canvas_id, msg)
        event_id = msg.id
    
    return RevisionResult(
        status="applied",
        current_rev=new_rev,
        your_rev=new_rev,
        event_id=event_id
    )
