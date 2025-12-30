"""WebSocket transport with strict auth/isolation and resume metadata."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Query,
    Depends,
    HTTPException,
    WebSocketException,
)

from engines.chat.contracts import Contact, Message
from engines.chat.pipeline import process_message
from engines.chat.service.transport_layer import bus
from engines.common.identity import RequestContext
from engines.identity.auth import AuthContext, get_optional_auth_context
from engines.identity.ticket_service import TicketError, validate_ticket
from engines.realtime.contracts import (
    EventIds,
    StreamEvent,
    RoutingKeys,
    ActorType,
    EventPriority,
    PersistPolicy,
    EventMeta,
    from_legacy_message,
)
from engines.realtime.timeline import get_timeline_store
from engines.realtime.isolation import verify_thread_access

router = APIRouter()
logger = logging.getLogger(__name__)


def _merge_scope(context_data: Dict[str, Any], ticket_payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    merged = {**(context_data or {})}
    ticket_payload = ticket_payload or {}
    required_fields = ("tenant_id", "mode", "project_id")
    for field in required_fields:
        value = merged.get(field) or ticket_payload.get(field)
        if not value:
            raise WebSocketException(code=4003, reason=f"{field} is required in hello context")
        if merged.get(field) and ticket_payload.get(field) and merged[field] != ticket_payload[field]:
            raise WebSocketException(code=4003, reason=f"{field} mismatch with ticket")
        merged[field] = value

    merged.setdefault("request_id", merged.get("trace_id") or ticket_payload.get("request_id") or uuid.uuid4().hex)
    for field in ("surface_id", "app_id", "user_id"):
        if merged.get(field) is None and ticket_payload.get(field) is not None:
            merged[field] = ticket_payload[field]
    return merged


def _context_from_scope(scope: Dict[str, Any]) -> RequestContext:
    try:
        ctx = RequestContext(
            tenant_id=scope["tenant_id"],
            mode=scope["mode"],
            project_id=scope["project_id"],
            request_id=scope.get("request_id") or uuid.uuid4().hex,
            surface_id=scope.get("surface_id"),
            app_id=scope.get("app_id"),
            user_id=scope.get("user_id"),
            actor_id=scope.get("user_id"),
        )
    except ValueError as exc:
        raise WebSocketException(code=4003, reason=str(exc)) from exc
    return ctx


def _resolve_hello_context(
    hello: Dict[str, Any],
    ticket_token: Optional[str],
    auth_context: Optional[AuthContext],
) -> tuple[RequestContext, Optional[str]]:
    if hello.get("type") != "hello":
        raise WebSocketException(code=4003, reason="first message must be type='hello'")

    ticket_payload: Optional[Dict[str, Any]] = None
    if ticket_token:
        try:
            ticket_payload = validate_ticket(ticket_token)
        except TicketError as exc:
            raise WebSocketException(code=4003, reason=str(exc)) from exc

    merged_scope = _merge_scope(hello.get("context") or {}, ticket_payload)
    ctx = _context_from_scope(merged_scope)
    if auth_context and auth_context.default_tenant_id != ctx.tenant_id:
        raise WebSocketException(code=4003, reason="Tenant mismatch")
    last_event_id = hello.get("last_event_id")
    return ctx, last_event_id


def _build_routing_keys(
    ctx: RequestContext, thread_id: str, actor_id: str, actor_type: ActorType
) -> RoutingKeys:
    return RoutingKeys(
        tenant_id=ctx.tenant_id,
        env=ctx.env,
        mode=ctx.mode,
        project_id=ctx.project_id,
        app_id=ctx.app_id,
        surface_id=ctx.surface_id,
        thread_id=thread_id,
        actor_id=actor_id,
        actor_type=actor_type,
    )


class ConnectionManager:
    def __init__(self) -> None:
        self.active: Dict[str, list[tuple[WebSocket, str]]] = {}

    async def connect(self, thread_id: str, websocket: WebSocket, user_id: str) -> None:
        self.active.setdefault(thread_id, []).append((websocket, user_id))
        logger.info(f"WS Connect: thread={thread_id} user={user_id}")

    def disconnect(self, thread_id: str, websocket: WebSocket) -> None:
        if thread_id in self.active:
            self.active[thread_id] = [
                (ws, uid) for ws, uid in self.active[thread_id] if ws != websocket
            ]
            if not self.active[thread_id]:
                del self.active[thread_id]

    async def broadcast_event(self, thread_id: str, event: StreamEvent) -> None:
        connections = self.active.get(thread_id, [])[:]
        payload = event.json()
        for ws, _ in connections:
            try:
                await ws.send_text(payload)
            except Exception:
                pass

    async def send_personal(self, websocket: WebSocket, payload: dict) -> None:
        try:
            await websocket.send_text(json.dumps(payload))
        except Exception:
            pass


manager = ConnectionManager()


async def heartbeat(websocket: WebSocket):
    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({"type": "ping"}))
    except Exception:
        pass


@router.websocket("/ws/chat/{thread_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    thread_id: str,
    ticket: Optional[str] = Query(None, alias="ticket"),
    auth_context: Optional[AuthContext] = Depends(get_optional_auth_context),
):
    await websocket.accept()
    try:
        hello = await websocket.receive_json()
    except Exception:
        await websocket.close(code=4003, reason="hello required")
        return

    ticket_token = hello.get("ticket") or ticket
    if not auth_context and not ticket_token:
        await websocket.close(code=4003, reason="Auth or ticket required")
        return

    try:
        request_context, last_event_id = _resolve_hello_context(
            hello,
            ticket_token,
            auth_context,
        )
    except WebSocketException as exc:
        await websocket.close(code=exc.code, reason=exc.reason)
        return

    user_id = (
        request_context.user_id
        or (auth_context.user_id if auth_context else None)
        or "anon"
    )
    request_context.user_id = user_id
    request_context.actor_id = user_id

    try:
        verify_thread_access(request_context.tenant_id, thread_id)
    except HTTPException as exc:
        await websocket.close(code=4003, reason=str(exc.detail))
        return

    await manager.connect(thread_id, websocket, user_id)
    hb_task = asyncio.create_task(heartbeat(websocket))

    timeline = get_timeline_store()
    replay_events = timeline.list_after(thread_id, after_event_id=last_event_id)
    cursor = last_event_id
    for event in replay_events:
        await manager.send_personal(websocket, json.loads(event.json()))
        cursor = event.event_id

    if cursor:
        resume_event = StreamEvent(
            type="resume_cursor",
            routing=_build_routing_keys(request_context, thread_id, user_id, ActorType.SYSTEM),
            data={"cursor": cursor},
            ids=EventIds(
                request_id=request_context.request_id,
                run_id=thread_id,
                step_id="resume_cursor",
            ),
            trace_id=request_context.request_id,
            meta=EventMeta(
                priority=EventPriority.INFO,
                persist=PersistPolicy.NEVER,
                last_event_id=cursor,
            ),
        )
        await manager.send_personal(websocket, json.loads(resume_event.json()))

    presence_event = StreamEvent(
        type="presence_state",
        routing=_build_routing_keys(request_context, thread_id, user_id, ActorType.HUMAN),
        data={"status": "online", "user_id": user_id},
        ids=EventIds(
            request_id=request_context.request_id,
            run_id=thread_id,
            step_id="presence_online",
        ),
        trace_id=request_context.request_id,
        meta=EventMeta(
            priority=EventPriority.INFO,
            persist=PersistPolicy.NEVER,
            last_event_id=None,
        ),
    )
    timeline.append(thread_id, presence_event, request_context)
    await manager.broadcast_event(thread_id, presence_event)

    def subscriber(msg: Message):
        event = from_legacy_message(
            msg,
            tenant_id=request_context.tenant_id,
            env=request_context.env,
            request_id=request_context.request_id,
            trace_id=request_context.request_id,
        )
        # import anyio
        # anyio.from_thread.run(manager.broadcast_event, thread_id, event)
        loop = asyncio.get_running_loop()
        loop.create_task(manager.broadcast_event(thread_id, event))

    sub_id = bus.subscribe(thread_id, subscriber)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "ping":
                await manager.send_personal(websocket, {"type": "pong"})

            elif msg_type == "message":
                sender = Contact(id=user_id)
                text = data.get("text", "")
                if text:
                    await process_message(thread_id, sender, text, context=request_context)

            elif msg_type == "gesture":
                gesture_event = StreamEvent(
                    type="gesture",
                    routing=_build_routing_keys(
                        request_context, thread_id, user_id, ActorType.HUMAN
                    ),
                    data=data.get("data", {}),
                    ids=EventIds(
                        request_id=request_context.request_id,
                        run_id=thread_id,
                        step_id="gesture",
                    ),
                    trace_id=request_context.request_id,
                    meta=EventMeta(
                        priority=EventPriority.GESTURE,
                        persist=PersistPolicy.NEVER,
                        last_event_id=None,
                    ),
                )

                from datetime import datetime
                bus_msg = Message(
                    id=gesture_event.event_id,
                    thread_id=thread_id,
                    sender=Contact(id=user_id),
                    text=gesture_event.json(),
                    role="system",
                    created_at=datetime.utcnow(),
                )

                bus.add_message(thread_id, bus_msg)
                timeline.append(thread_id, gesture_event, request_context)

            elif msg_type == "presence_ping":
                pass

    except WebSocketDisconnect:
        manager.disconnect(thread_id, websocket)
        leave_event = StreamEvent(
            type="presence_state",
            routing=_build_routing_keys(request_context, thread_id, user_id, ActorType.HUMAN),
            data={"status": "offline", "user_id": user_id},
            ids=EventIds(
                request_id=request_context.request_id,
                run_id=thread_id,
                step_id="presence_offline",
            ),
            trace_id=request_context.request_id,
            meta=EventMeta(
                priority=EventPriority.INFO,
                persist=PersistPolicy.NEVER,
                last_event_id=None,
            ),
        )
        timeline.append(thread_id, leave_event, request_context)
        await manager.broadcast_event(thread_id, leave_event)
    except Exception:
        manager.disconnect(thread_id, websocket)
    finally:
        hb_task.cancel()
        bus.unsubscribe(thread_id, sub_id)
