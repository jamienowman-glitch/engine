"""Authenticated SSE transport wired to the chat pipeline."""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Header, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from engines.chat.contracts import Contact
from engines.chat.store_service import chat_store_or_503
from engines.chat.service.transport_layer import subscribe_async
from engines.chat.pipeline import process_message
from engines.common.error_envelope import error_response
from engines.common.identity import RequestContext, assert_context_matches, get_request_context
from engines.identity.auth import AuthContext, get_auth_context, get_optional_auth_context
from engines.identity.ticket_service import TicketError, context_from_ticket
from engines.realtime.contracts import (
    ActorType,
    EventIds,
    EventMeta,
    EventPriority,
    PersistPolicy,
    RoutingKeys,
    StreamEvent,
    from_legacy_message,
)
from engines.realtime.isolation import verify_thread_access

router = APIRouter()
logger = logging.getLogger(__name__)


def _format_sse_event(event: StreamEvent) -> str:
    payload = event.json()
    return f"id: {event.event_id}\nevent: {event.type}\ndata: {payload}\n\n"


def _build_resume_event(thread_id: str, context: RequestContext, cursor: str) -> StreamEvent:
    routing = RoutingKeys(
        tenant_id=context.tenant_id,
        env=context.env,
        mode=context.mode,
        project_id=context.project_id,
        app_id=context.app_id,
        surface_id=context.surface_id,
        thread_id=thread_id,
        actor_id=context.user_id or "system",
        actor_type=ActorType.SYSTEM,
    )
    return StreamEvent(
        type="resume_cursor",
        event_id=f"resume-{cursor or uuid.uuid4().hex}",
        routing=routing,
        data={"cursor": cursor},
        ids=EventIds(
            request_id=context.request_id,
            run_id=thread_id,
            step_id="resume_cursor",
        ),
        trace_id=context.request_id,
        meta=EventMeta(
            priority=EventPriority.INFO,
            persist=PersistPolicy.NEVER,
            last_event_id=cursor,
        ),
    )


async def _chat_stream_with_resume(
    thread_id: str,
    request_context: RequestContext,
    last_event_id: Optional[str],
    *,
    store=None,
    validate_cursor: bool = True,
) -> AsyncGenerator[str, None]:
    store = store or chat_store_or_503(request_context)
    if validate_cursor and last_event_id:
        store.list_messages(thread_id, after_cursor=last_event_id, limit=1)

    latest_cursor = store.latest_cursor(thread_id)
    if latest_cursor:
        resume_event = _build_resume_event(thread_id, request_context, latest_cursor)
        yield _format_sse_event(resume_event)

    async for chunk in event_stream(
        thread_id=thread_id,
        request_context=request_context,
        last_event_id=last_event_id,
    ):
        yield chunk


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
        yield _format_sse_event(event)
        await asyncio.sleep(0)


def _require_identity_header(value: Optional[str], header_name: str, code: str) -> None:
    if not value:
        error_response(
            code=code,
            message=f"{header_name} header is required",
            status_code=400,
            resource_kind="chat",
        )


def _enforce_stream_identity(
    context: RequestContext,
    header_mode: Optional[str],
    header_project: Optional[str],
    header_app: Optional[str],
    query_tenant: Optional[str],
    query_project: Optional[str],
    query_surface: Optional[str],
    query_app: Optional[str],
) -> None:
    _require_identity_header(header_mode, "X-Mode", "auth.mode_missing")
    _require_identity_header(header_project, "X-Project-Id", "auth.project_missing")
    _require_identity_header(header_app, "X-App-Id", "auth.app_missing")
    try:
        assert_context_matches(
            context,
            tenant_id=query_tenant,
            mode=header_mode,
            project_id=query_project,
            surface_id=query_surface,
            app_id=query_app,
        )
    except HTTPException as exc:
        error_response(
            code="auth.context_mismatch",
            message=str(exc.detail),
            status_code=exc.status_code,
            resource_kind="chat",
            details={
                "provided": {
                    "tenant_id": query_tenant,
                    "project_id": query_project,
                    "surface_id": query_surface,
                    "app_id": query_app,
                },
            },
        )

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
            error_response(
                code="auth.ticket_invalid",
                message=str(exc),
                status_code=401,
                resource_kind="chat",
            )

    _require_identity_header(header_mode, "X-Mode", "auth.mode_missing")
    _require_identity_header(header_project, "X-Project-Id", "auth.project_missing")
    _require_identity_header(header_app, "X-App-Id", "auth.app_missing")

    context = await get_request_context(
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
    _enforce_stream_identity(
        context,
        header_mode,
        header_project,
        header_app,
        query_tenant,
        query_project,
        query_surface,
        query_app,
    )
    return context


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
        error_response(
            code="auth.ticket_missing",
            message="Auth or ticket required",
            status_code=401,
            resource_kind="chat",
        )
    if auth_context and auth_context.default_tenant_id != request_context.tenant_id:
        logger.warning(
            "SSE Auth mismatch: %s != %s",
            auth_context.default_tenant_id,
            request_context.tenant_id,
        )
        error_response(
            code="auth.tenant_mismatch",
            message="Tenant mismatch",
            status_code=403,
            resource_kind="chat",
        )

    verify_thread_access(request_context.tenant_id, thread_id)

    store = chat_store_or_503(request_context)
    if cursor:
        store.list_messages(thread_id, after_cursor=cursor, limit=1)

    return StreamingResponse(
        _chat_stream_with_resume(
            thread_id=thread_id,
            request_context=request_context,
            last_event_id=cursor,
            store=store,
            validate_cursor=False,
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
