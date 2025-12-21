"""Service for handling canvas commands with strict concurrency control."""
from __future__ import annotations

import logging
import asyncio
from typing import Dict, Optional, List, Set

from fastapi import HTTPException
from engines.canvas_commands.models import CommandEnvelope, RevisionResult
from engines.realtime.contracts import StreamEvent, RoutingKeys, ActorType, EventPriority, PersistPolicy
from engines.chat.service.transport_layer import bus
from engines.realtime.isolation import verify_canvas_access

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
    command: CommandEnvelope
) -> RevisionResult:
    """
    Apply a command to a canvas strictly checking base_rev.
    """
    # 1. Isolation Check
    verify_canvas_access(tenant_id, command.canvas_id)
    
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
    # The command service is the source of truth for the event stream.
    event = StreamEvent(
        type="canvas_commit",
        routing=RoutingKeys(
            tenant_id=tenant_id,
            env="dev", # derived or passed
            canvas_id=command.canvas_id,
            actor_id=user_id,
            actor_type=ActorType.HUMAN
        ),
        data={
            "cmd_id": command.id,
            "type": command.type,
            "args": command.args,
            "rev": new_rev
        }
    )
    
    # Publish to bus so SSE transport picks it up
    # Note: bus expects Message, subscriber in SSE/Router adapts it.
    # This is "double wrapping" or we need to fix bus to support direct events.
    # For now, we wrap in Message.text to match current Adapter pattern.
    from engines.chat.contracts import Message, Contact
    from datetime import datetime
    
    msg = Message(
        id=event.event_id,
        thread_id=command.canvas_id, # Bus topic
        sender=Contact(id=user_id),
        text=event.json(), # serialized StreamEvent or internal dict
        role="system",
        created_at=datetime.utcnow()
    )
    
    # We put the "kind" in the payload so the Router knows it's a commit
    # Ideally the router just forwards the StreamEvent if we serialize it here.
    # But router.py logic currently tries to load JSON and look for "kind".
    # If we put the WHOLE StreamEvent in text, the router might double-wrap it if not careful.
    # Let's align with router.py: 
    # Router says: content = json.loads(msg.text); kind = content.get("kind")
    # So we should put valid content dict here.
    
    final_payload = {
        "kind": "canvas_commit",
        "cmd_id": command.id,
        "type": command.type,
        "rev": new_rev,
        "args": command.args
    }
    msg.text = import_json().dumps(final_payload)
    
    # In-memory bus is synchronous
    bus.add_message(command.canvas_id, msg)
    
    return RevisionResult(
        status="applied",
        current_rev=new_rev,
        your_rev=new_rev,
        event_id=event.event_id
    )

def import_json():
    import json
    return json
