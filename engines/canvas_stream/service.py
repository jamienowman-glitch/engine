from __future__ import annotations

import asyncio
from typing import AsyncGenerator
import json
from engines.chat.service.transport_layer import bus, subscribe_async
from engines.chat.contracts import Message, Contact
from engines.canvas_stream.models import GestureEvent
from engines.feature_flags.service import get_feature_flags

# Reusing In-Memory Bus for Phase 02 as planned.
# Canvas streams are effectively threads with specific ID patterns.

async def publish_gesture(
    canvas_id: str, 
    gesture: GestureEvent, 
    tenant_id: str, 
    env: str
) -> bool:
    """
    Publish gesture respecting feature flags.
    Returns True if published/logged, False if dropped.
    """
    # L1-T3: Auto-register canvas
    from engines.realtime.isolation import register_canvas_resource
    register_canvas_resource(tenant_id, canvas_id)

    flags = await get_feature_flags(tenant_id, env)
    
    import uuid
    # 1. Check Visibility/Logging
    # If explicitly disabled, drop
    # Treat "private" same as "off" for drop logic if logging is also disabled?
    # Or "private" means "log but don't fanout"?
    # Test expectation for 'disabled' case was "False" returned. 
    # Let's align code: if not logging and mode in ["off", "private"]: drop
    if not flags.gesture_logging and flags.visibility_mode in ["off", "private"]:
        return False

    # 2. Live Fanout
    # Fanout only if NOT private/off
    should_fanout = (flags.visibility_mode not in ["off", "private"])
    
    if should_fanout:
        # Wrap in Message contract
        payload = json.dumps({"type": "gesture", "data": gesture.dict(exclude_none=True)}, default=str)
        sender = Contact(id=gesture.actor_id)
        msg = Message(
            id=uuid.uuid4().hex, # Auto-gen ID
            thread_id=canvas_id,
            sender=sender,
            text=payload,
            role="system"
        )
        bus.add_message(canvas_id, msg)
        
    # 3. Logging / Replay Artifact
    if flags.gesture_logging:
        # TODO: Append to replay buffer/db
        # For Phase 05 we just acknowledge the logic is here.
        # Ideally: replay_repo.append(canvas_id, gesture)
        pass

    return True

def publish_canvas_event(canvas_id: str, event_type: str, data: dict, actor_id: str, tenant_id: str):
    """Publish a canvas event (commit, gesture, etc)."""
    # Wrap in Message contract for bus compatibility or extend contract?
    # Keeping it simple: Text payload with structured JSON.
    
    # L1-T3: Auto-register canvas
    from engines.realtime.isolation import register_canvas_resource
    register_canvas_resource(tenant_id, canvas_id)

    import json
    payload = json.dumps({"type": event_type, "data": data})
    
    import uuid
    sender = Contact(id=actor_id)
    msg = Message(
        id=uuid.uuid4().hex,
        thread_id=canvas_id,
        sender=sender,
        text=payload,
        role="system" # Canvas events are system or specially role'd
    )
    # Bus auto-IDs
    bus.add_message(canvas_id, msg)
    return msg

async def subscribe_canvas(canvas_id: str, last_event_id: str | None = None) -> AsyncGenerator[Message, None]:
    async for msg in subscribe_async(canvas_id, last_event_id):
        yield msg
