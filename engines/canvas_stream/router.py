from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Header, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from engines.chat.store_service import chat_store_or_503
from engines.canvas_stream.service import subscribe_canvas
from engines.common.error_envelope import error_response, cursor_invalid_error
from engines.common.identity import RequestContext, get_request_context
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
)
from engines.realtime.isolation import verify_canvas_access

router = APIRouter(prefix="/sse/canvas", tags=["canvas-stream"])
logger = logging.getLogger(__name__)


def _format_sse_event(event: StreamEvent) -> str:
    payload = event.json()
    return f"id: {event.event_id}\nevent: {event.type}\ndata: {payload}\n\n"


def _build_resume_event(canvas_id: str, context: RequestContext, cursor: str) -> StreamEvent:
    return StreamEvent(
        type="resume_cursor",
        event_id=f"resume-{cursor or uuid.uuid4().hex}",
        routing=RoutingKeys(
            tenant_id=context.tenant_id,
            env=context.env,
            mode=context.mode,
            project_id=context.project_id,
            app_id=context.app_id,
            surface_id=context.surface_id,
            canvas_id=canvas_id,
            actor_id=context.user_id or "system",
            actor_type=ActorType.SYSTEM,
        ),
        data={"cursor": cursor},
        ids=EventIds(
            request_id=context.request_id,
            run_id=canvas_id,
            step_id="resume_cursor",
        ),
        trace_id=context.request_id,
        meta=EventMeta(
            priority=EventPriority.INFO,
            persist=PersistPolicy.NEVER,
            last_event_id=cursor,
        ),
    )


async def _canvas_stream_with_resume(
    canvas_id: str,
    request_context: RequestContext,
    last_event_id: Optional[str],
) -> AsyncGenerator[str, None]:
    store = chat_store_or_503(request_context)
    if last_event_id:
        try:
            store.list_messages(canvas_id, after_cursor=last_event_id, limit=1)
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            error_code = detail.get("error", {}).get("code") if isinstance(detail, dict) else None
            if error_code == "chat.cursor_invalid":
                raise cursor_invalid_error(last_event_id, domain="canvas")
            raise

    latest_cursor = store.latest_cursor(canvas_id)
    if latest_cursor:
        resume_event = _build_resume_event(canvas_id, request_context, latest_cursor)
        yield _format_sse_event(resume_event)

    async for chunk in event_stream(
        canvas_id=canvas_id,
        request_context=request_context,
        last_event_id=last_event_id,
    ):
        yield chunk


async def _canvas_context(
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
                resource_kind="canvas",
            )

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

        yield _format_sse_event(event)
        await asyncio.sleep(0)


@router.get("/{canvas_id}")
async def stream_canvas(
    canvas_id: str,
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
    request_context: RequestContext = Depends(_canvas_context),
    auth_context: Optional[AuthContext] = Depends(get_optional_auth_context),
    ticket: Optional[str] = Query(default=None, alias="ticket"),
) -> StreamingResponse:
    if not auth_context and not ticket:
        error_response(
            code="auth.ticket_missing",
            message="Auth or ticket required",
            status_code=401,
            resource_kind="canvas",
        )
    if auth_context and auth_context.default_tenant_id != request_context.tenant_id:
        error_response(
            code="auth.tenant_mismatch",
            message="Tenant mismatch",
            status_code=403,
            resource_kind="canvas",
        )

    # Lane 2: Minimal Read Access Check
    verify_canvas_access(request_context.tenant_id, canvas_id)

    # Durability: Wrap generator to catch mid-stream errors
    async def durable_stream():
        try:
            async for chunk in _canvas_stream_with_resume(
                canvas_id=canvas_id,
                request_context=request_context,
                last_event_id=last_event_id,
            ):
                yield chunk
        except Exception as e:
            logger.exception("Stream crashed for canvas %s", canvas_id)
            # Attempt to emit error event before closing
            error_event = StreamEvent(
                type="error",
                event_id=uuid.uuid4().hex,
                routing=RoutingKeys(
                    tenant_id=request_context.tenant_id,
                    env=request_context.env,
                    mode=request_context.mode,
                    project_id=request_context.project_id,
                    app_id=request_context.app_id,
                    surface_id=request_context.surface_id,
                    canvas_id=canvas_id,
                    actor_id="system",
                    actor_type=ActorType.SYSTEM,
                ),
                data={
                     "code": "stream.crash",
                     "message": "Stream interrupted by internal error",
                     "details": str(e)
                },
                meta=EventMeta(priority=EventPriority.CRITICAL, persist=PersistPolicy.NEVER),
            )
            yield _format_sse_event(error_event)

    return StreamingResponse(
        durable_stream(),
        media_type="text/event-stream",
    )
