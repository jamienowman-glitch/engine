from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Header, Depends, HTTPException
from fastapi.responses import StreamingResponse

from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context
from engines.canvas_stream.service import subscribe_canvas
from engines.realtime.contracts import (
    StreamEvent, RoutingKeys, ActorType, EventIds, EventMeta, EventPriority, PersistPolicy
)
from engines.realtime.isolation import verify_canvas_access

router = APIRouter(prefix="/sse/canvas", tags=["canvas-stream"])
logger = logging.getLogger(__name__)


async def event_stream(
    canvas_id: str, 
    request_context: RequestContext,
    last_event_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    async for msg in subscribe_canvas(canvas_id, request_context, last_event_id=last_event_id):
        # Canvas messages might be wrapped JSON in 'text' from the message bus
        # We need to construct a proper StreamEvent.
        # Ideally, `subscribe_canvas` would yield StreamEvents directly, but it relies on `InMemoryBus` (legacy Message).
        # We unwrap and re-wrap strictly.
        
        content = {}
        try:
            content = json.loads(msg.text)
        except:
            content = {"raw": msg.text}
        
        # Determine event type from content or default to 'canvas_commit'
        # The content might be a "GestureEvent" dict or "Commit" dict.
        # We look for "kind" in content.
        
        kind = content.get("type") or content.get("kind")
        if not kind and {"action", "result", "gate"}.issubset(content.keys()):
            kind = "SAFETY_DECISION"
        kind = kind or "canvas_commit"
        
        # Build strict StreamEvent
        event = StreamEvent(
            type=kind,
            ts=msg.created_at,
            event_id=msg.id,
            routing=RoutingKeys(
                tenant_id=request_context.tenant_id,
                env=request_context.env, # type: ignore
                mode=request_context.mode,
                project_id=request_context.project_id,
                app_id=request_context.app_id,
                surface_id=request_context.surface_id,
                canvas_id=canvas_id,
                actor_id=msg.sender.id,
                # Assume human for now, or infer from sender ID prefix
                actor_type=ActorType.AGENT if msg.sender.id.startswith("agent-") else ActorType.HUMAN
            ),
            data=content,
            meta=EventMeta(
                # If gesture, ephemeral?
                priority=EventPriority.GESTURE if "gesture" in kind else EventPriority.TRUTH,
                persist=PersistPolicy.NEVER if "gesture" in kind else PersistPolicy.ALWAYS
            )
        )

        payload = event.json()
        yield f"id: {event.event_id}\nevent: {event.type}\ndata: {payload}\n\n"
        await asyncio.sleep(0)


@router.get("/{canvas_id}")
async def stream_canvas(
    canvas_id: str,
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
) -> StreamingResponse:
    # 1. Auth/Tenant Check
    if auth_context.default_tenant_id != request_context.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
        
    # 2. Strict Isolation
    verify_canvas_access(request_context.tenant_id, canvas_id)
    
    # 3. Stream
    return StreamingResponse(
        event_stream(
            canvas_id=canvas_id,
            request_context=request_context,
            last_event_id=last_event_id
        ),
        media_type="text/event-stream"
    )
