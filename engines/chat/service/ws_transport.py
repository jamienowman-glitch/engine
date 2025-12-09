"""WebSocket transport wired to chat pipeline."""
from __future__ import annotations

import json
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from engines.chat.contracts import Contact
from engines.chat.pipeline import process_message
from engines.chat.service.transport_layer import bus

router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self.active: Dict[str, list[WebSocket]] = {}

    async def connect(self, thread_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.setdefault(thread_id, []).append(websocket)

    def disconnect(self, thread_id: str, websocket: WebSocket) -> None:
        conns = self.active.get(thread_id, [])
        if websocket in conns:
            conns.remove(websocket)

    async def broadcast(self, thread_id: str, payload: dict) -> None:
        for ws in self.active.get(thread_id, []):
            await ws.send_text(json.dumps(payload))


manager = ConnectionManager()


@router.websocket("/ws/chat/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    await manager.connect(thread_id, websocket)

    def subscriber(msg):
        payload = {"type": "message", "data": msg.dict()}
        import anyio

        anyio.from_thread.run(manager.broadcast, thread_id, payload)  # type: ignore[arg-type]

    sub_id = bus.subscribe(thread_id, subscriber)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "join":
                await manager.broadcast(thread_id, {"type": "join", "data": data.get("user")})
            elif data.get("type") == "message":
                sender = Contact(id=data.get("sender_id", "user"))
                text = data.get("text", "")
                msgs = process_message(thread_id, sender, text)
                for m in msgs:
                    await manager.broadcast(thread_id, {"type": "message", "data": m.dict()})
    except WebSocketDisconnect:
        manager.disconnect(thread_id, websocket)
    finally:
        bus.unsubscribe(thread_id, sub_id)
