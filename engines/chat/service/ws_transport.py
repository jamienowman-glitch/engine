"""WebSocket transport with strict auth/isolation and resume metadata."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Optional

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Query,
    Depends,
    HTTPException,
    WebSocketException,
    Request,
)

from engines.chat.contracts import Contact, Message
from engines.chat.pipeline import process_message
from engines.chat.service.transport_layer import bus
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context
from engines.realtime.contracts import (
    StreamEvent,
    RoutingKeys,
    ActorType,
    EventPriority,
    PersistPolicy,
    EventMeta,
    from_legacy_message,
)
from engines.realtime.isolation import verify_thread_access

router = APIRouter()
logger = logging.getLogger(__name__)


async def _websocket_request_context(websocket: WebSocket) -> RequestContext:
    scope = dict(websocket.scope)
    scope["type"] = "http"
    scope["method"] = "GET"

    async def _receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    request = Request(scope, receive=_receive)
    try:
        headers = {
            key.decode().lower(): value.decode()
            for key, value in websocket.scope.get("headers", [])
        }
        return await get_request_context(
            request,
            header_tenant=headers.get("x-tenant-id"),
            header_env=headers.get("x-env"),
            header_user=headers.get("x-user-id"),
            header_role=headers.get("x-membership-role"),
            header_request_id=headers.get("x-request-id"),
            authorization=headers.get("authorization"),
            query_tenant=None,
            query_env=None,
            query_user=None,
        )
    except HTTPException as exc:
        raise WebSocketException(code=4003, reason=str(exc.detail)) from exc


async def _websocket_auth_context(websocket: WebSocket) -> AuthContext:
    authorization = websocket.headers.get("authorization")
    if not authorization:
        raise WebSocketException(code=4003, reason="Auth Required")
    try:
        return get_auth_context(authorization)
    except HTTPException as exc:
        raise WebSocketException(code=4003, reason=str(exc.detail)) from exc


def _build_routing_keys(
    ctx: RequestContext, thread_id: str, actor_id: str, actor_type: ActorType
) -> RoutingKeys:
    return RoutingKeys(
        tenant_id=ctx.tenant_id,
        env=ctx.env,
        mode=ctx.env,
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
        await websocket.accept()
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
    last_event_id: Optional[str] = Query(None, alias="last_event_id"),
    request_context: RequestContext = Depends(_websocket_request_context),
    auth_context: AuthContext = Depends(_websocket_auth_context),
):
    user_id = request_context.user_id or auth_context.user_id or "anon"
    request_context.user_id = user_id

    if auth_context.default_tenant_id != request_context.tenant_id:
        logger.warning(
            "WS tenant mismatch: %s != %s",
            auth_context.default_tenant_id,
            request_context.tenant_id,
        )
        await websocket.close(code=4003, reason="Tenant mismatch")
        return

    try:
        verify_thread_access(request_context.tenant_id, thread_id)
    except HTTPException as exc:
        await websocket.close(code=4003, reason=str(exc.detail))
        return

    await manager.connect(thread_id, websocket, user_id)
    hb_task = asyncio.create_task(heartbeat(websocket))

    missed_messages = bus.get_messages(thread_id, after_id=last_event_id)
    for msg in missed_messages:
        event = from_legacy_message(
            msg,
            tenant_id=request_context.tenant_id,
            env=request_context.env,
            request_id=request_context.request_id,
            trace_id=request_context.request_id,
        )
        await manager.send_personal(websocket, json.loads(event.json()))

    cursor = missed_messages[-1].id if missed_messages else last_event_id
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
    await manager.broadcast_event(thread_id, presence_event)

    def subscriber(msg: Message):
        event = from_legacy_message(
            msg,
            tenant_id=request_context.tenant_id,
            env=request_context.env,
            request_id=request_context.request_id,
            trace_id=request_context.request_id,
        )
        import anyio
        anyio.from_thread.run(manager.broadcast_event, thread_id, event)

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
                    await process_message(thread_id, sender, text)

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
        await manager.broadcast_event(thread_id, leave_event)
    except Exception:
        manager.disconnect(thread_id, websocket)
    finally:
        hb_task.cancel()
        bus.unsubscribe(thread_id, sub_id)
