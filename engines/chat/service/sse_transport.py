"""Authenticated SSE transport wired to the chat pipeline."""
from __future__ import annotations

import asyncio
import logging
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Header, Depends, HTTPException
from fastapi.responses import StreamingResponse

from engines.chat.contracts import Contact
from engines.chat.pipeline import process_message
from engines.chat.service.transport_layer import subscribe_async
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context
from engines.realtime.contracts import StreamEvent, from_legacy_message, EventPriority, PersistPolicy
from engines.realtime.isolation import verify_thread_access

router = APIRouter()
logger = logging.getLogger(__name__)


async def event_stream(
    thread_id: str,
    request_context: RequestContext,
    last_event_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    Yields strictly formatted SSE events (StreamEvent JSON) and attaches trace metadata.
    """
    async for msg in subscribe_async(thread_id, last_event_id=last_event_id):
        event = from_legacy_message(
            msg,
            tenant_id=request_context.tenant_id,
            env=request_context.env,
            request_id=request_context.request_id,
            trace_id=request_context.request_id,
        )
        payload = event.json()
        yield f"id: {event.event_id}\nevent: {event.type}\ndata: {payload}\n\n"
        await asyncio.sleep(0)


@router.get("/sse/chat/{thread_id}")
async def sse_chat(
    thread_id: str,
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
) -> StreamingResponse:
    if auth_context.default_tenant_id != request_context.tenant_id:
        logger.warning(
            "SSE Auth mismatch: %s != %s",
            auth_context.default_tenant_id,
            request_context.tenant_id,
        )
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    verify_thread_access(request_context.tenant_id, thread_id)

    return StreamingResponse(
        event_stream(
            thread_id=thread_id,
            request_context=request_context,
            last_event_id=last_event_id,
        ),
        media_type="text/event-stream",
    )


@router.post("/sse/chat/{thread_id}")
async def post_message(
    thread_id: str,
    sender: Contact,
    text: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    if sender.id != auth_context.user_id:
        raise HTTPException(status_code=403, detail="Sender mismatch")

    verify_thread_access(request_context.tenant_id, thread_id)

    msgs = await process_message(thread_id, sender, text)
    return {"posted": [m.dict() for m in msgs]}
