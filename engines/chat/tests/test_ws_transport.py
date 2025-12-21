"""Unit tests ensuring a ConnectionManager event delivery behaves as expected."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass

from engines.chat.service.ws_transport import ConnectionManager
from engines.realtime.contracts import (
    ActorType,
    EventMeta,
    EventPriority,
    PersistPolicy,
    RoutingKeys,
    StreamEvent,
)


@dataclass
class _FakeWebSocket:
    sent: list[str] | None = None

    def __post_init__(self) -> None:
        self.sent = []

    async def send_text(self, payload: str) -> None:
        self.sent.append(payload)


def _build_event() -> StreamEvent:
    return StreamEvent(
        type="presence_state",
        routing=RoutingKeys(
            tenant_id="t_demo",
            env="dev",
            thread_id="thread-ws-clean",
            actor_id="u1",
            actor_type=ActorType.HUMAN,
        ),
        data={"status": "online"},
        trace_id="trace-ws-1",
        meta=EventMeta(priority=EventPriority.INFO, persist=PersistPolicy.NEVER),
    )


def test_connection_manager_broadcasts_event() -> None:
    manager = ConnectionManager()
    ws = _FakeWebSocket()
    manager.active.setdefault("thread-ws-clean", []).append((ws, "u1"))
    asyncio.run(manager.broadcast_event("thread-ws-clean", _build_event()))
    assert ws.sent
    payload = json.loads(ws.sent[0])
    assert payload["trace_id"] == "trace-ws-1"
    assert payload["routing"]["tenant_id"] == "t_demo"
