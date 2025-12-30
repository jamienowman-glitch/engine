"""Authenticated SSE transport wired to the chat pipeline."""
from __future__ import annotations

import asyncio
import logging
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Header, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from engines.chat.contracts import Contact
from engines.chat.pipeline import process_message
from engines.chat.service.transport_layer import subscribe_async
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context, get_optional_auth_context
from engines.identity.ticket_service import TicketError, context_from_ticket
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
    async for msg in subscribe_async(thread_id, last_event_id=last_event_id, context=request_context):
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

async def _sse_context(
    request: Request,
    ticket: Optional[str] = Query(default=None, alias="ticket"),
    header_tenant: Optional[str] = Header(default=None, alias="X-Tenant-Id"),
    header_mode: Optional[str] = Header(default=None, alias="X-Mode"),
    header_project: Optional[str] = Header(default=None, alias="X-Project-Id"),
    header_surface: Optional[str] = Header(default=None, alias="X-Surface-Id"),
    header_app: Optional[str] = Header(default=None, alias="X-App-Id"),
    header_user: Optional[str] = Header(default=None, alias="X-User-Id"),
    header_role: Optional[str] = Header(default=None, alias="X-Membership-Role"),
    header_request_id: Optional[str] = Header(default=None, alias="X-Request-Id"),
    header_env: Optional[str] = Header(default=None, alias="X-Env"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    query_tenant: Optional[str] = Query(default=None, alias="tenant_id"),
    query_project: Optional[str] = Query(default=None, alias="project_id"),
    query_surface: Optional[str] = Query(default=None, alias="surface_id"),
    query_app: Optional[str] = Query(default=None, alias="app_id"),
    query_user: Optional[str] = Query(default=None, alias="user_id"),
) -> RequestContext:
    if ticket:
        try:
            return context_from_ticket(ticket)
        except TicketError as exc:
            raise HTTPException(status_code=401, detail=str(exc))

    return await get_request_context(
        request,
        header_tenant=header_tenant,
        header_mode=header_mode,
        header_project=header_project,
        header_surface=header_surface,
        header_app=header_app,
        header_user=header_user,
        header_role=header_role,
        header_request_id=header_request_id,
        header_env=header_env,
        authorization=authorization,
        query_tenant=query_tenant,
        query_project=query_project,
        query_surface=query_surface,
        query_app=query_app,
        query_user=query_user,
    )


@router.get("/sse/chat/{thread_id}")
async def sse_chat(
    thread_id: str,
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
    query_last_event_id: Optional[str] = Query(None, alias="last_event_id"),
    request_context: RequestContext = Depends(_sse_context),
    auth_context: Optional[AuthContext] = Depends(get_optional_auth_context),
    ticket: Optional[str] = Query(default=None, alias="ticket"),
) -> StreamingResponse:
    cursor = last_event_id or query_last_event_id
    if not auth_context and not ticket:
        raise HTTPException(status_code=401, detail="Auth or ticket required")
    if auth_context and auth_context.default_tenant_id != request_context.tenant_id:
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
            last_event_id=cursor,
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

    msgs = await process_message(thread_id, sender, text, context=request_context)
    return {"posted": [m.dict() for m in msgs]}
