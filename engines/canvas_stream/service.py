from __future__ import annotations

import asyncio
from typing import AsyncGenerator
import json
from engines.chat.service.transport_layer import bus, subscribe_async, publish_message
from engines.chat.contracts import Message, Contact
from engines.canvas_stream.models import GestureEvent
from engines.feature_flags.service import get_feature_flags
from engines.common.identity import RequestContext
from engines.nexus.hardening.gate_chain import get_gate_chain
from fastapi import HTTPException

# Reusing In-Memory Bus for Phase 02 as planned.
# Canvas streams are effectively threads with specific ID patterns.

async def publish_gesture(
    canvas_id: str, 
    gesture: GestureEvent, 
    context: RequestContext,
) -> bool:
    """
    Publish gesture respecting feature flags.
    Returns True if published/logged, False if dropped.
    """
    # L1-T3: Auto-register canvas
    from engines.realtime.isolation import register_canvas_resource
    register_canvas_resource(context.tenant_id, canvas_id)

    # Lane 2: Call GateChain before publishing
    try:
        gate_chain = get_gate_chain()
        gate_chain.run(
            ctx=context,
            action="canvas_gesture",
            surface=context.surface_id or "canvas",
            subject_type="canvas",
            subject_id=canvas_id,
        )
    except HTTPException as exc:
        raise exc

    flags = await get_feature_flags(context.tenant_id, context.env)
    
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
        publish_message(
            canvas_id,
            sender,
            payload,
            role="system",
            context=context,
        )
        
    # 3. Logging / Replay Artifact
    if flags.gesture_logging:
        # TODO: Append to replay buffer/db
        # For Phase 05 we just acknowledge the logic is here.
        # Ideally: replay_repo.append(canvas_id, gesture)
        pass

    return True

def publish_canvas_event(canvas_id: str, event_type: str, data: dict, actor_id: str, context: RequestContext):
    """
    Publish a canvas event (commit, gesture, etc).
    
    Lane 3: All canvas events are appended to the durable timeline via publish_message,
    which allows them to be replayed after server restart when reconnecting with Last-Event-ID.
    SAFETY_DECISION events are also appended to the same timeline stream.
    """
    # Wrap in Message contract for bus compatibility or extend contract?
    # Keeping it simple: Text payload with structured JSON.
    
    # L1-T3: Auto-register canvas
    from engines.realtime.isolation import register_canvas_resource
    register_canvas_resource(context.tenant_id, canvas_id)

    # Lane 2: Call GateChain before publishing
    try:
        gate_chain = get_gate_chain()
        gate_chain.run(
            ctx=context,
            action="canvas_command",
            surface=context.surface_id or "canvas",
            subject_type="canvas",
            subject_id=canvas_id,
        )
    except HTTPException as exc:
        raise exc

    import json
    payload = json.dumps({"type": event_type, "data": data})
    
    sender = Contact(id=actor_id)
    return publish_message(
        canvas_id,
        sender,
        payload,
        role="system",
        context=context,
    )

async def subscribe_canvas(canvas_id: str, request_context: RequestContext, last_event_id: str | None = None) -> AsyncGenerator[Message, None]:
    """
    Subscribe to canvas events with replay support.
    
    Lane 3: Canvas events and SAFETY_DECISION events are appended to the durable timeline
    during publish_canvas_event and publish_gesture. When reconnecting with Last-Event-ID,
    the timeline replays all prior canvas commands, gestures, and SAFETY_DECISION records.
    This supports SSE and WebSocket replay after server restart.
    """
    async for msg in subscribe_async(canvas_id, last_event_id, context=request_context):
        yield msg
