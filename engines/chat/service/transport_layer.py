"""Durable-aware pub/sub for chat transports (PLAN-024 stubs)."""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, Callable, Dict, List, Tuple

from engines.chat.contracts import Message, Thread, Contact, ChatScope
from engines.common.identity import RequestContext
from engines.realtime.contracts import (
    StreamEvent,
    EventIds,
    RoutingKeys,
    ActorType,
    EventMeta,
    EventPriority,
    PersistPolicy,
)
from engines.realtime.timeline import get_timeline_store


class InMemoryBus:
    def __init__(self) -> None:
        self.threads: Dict[str, Thread] = {}
        # Key: thread_id -> List[Message]
        self.messages: Dict[str, List[Message]] = {}
        # Key: thread_id -> List[(sub_id, callback)]
        self.subscribers: Dict[str, List[Tuple[str, Callable[[Message], Any]]]] = {}

    def create_thread(self, participants: List[Contact]) -> Thread:
        thread_id = uuid.uuid4().hex
        thread = Thread(id=thread_id, participants=participants)
        self.threads[thread_id] = thread
        self.messages[thread_id] = []
        return thread

    def list_threads(self) -> List[Thread]:
        return list(self.threads.values())

    def add_message(self, thread_id: str, msg: Message) -> None:
        if thread_id not in self.messages:
            self.messages[thread_id] = []
        self.messages[thread_id].append(msg)
        for _, callback in self.subscribers.get(thread_id, []):
            try:
                callback(msg)
            except Exception:
                # Best effort delivery
                pass

    def get_messages(self, thread_id: str, after_id: str | None = None) -> List[Message]:
        msgs = self.messages.get(thread_id, [])
        if not after_id:
            return msgs
        
        # Simple seek for replay
        try:
            # Find index of after_id
            for i, m in enumerate(msgs):
                if m.id == after_id:
                    return msgs[i+1:]
        except Exception:
            pass
        return []

    def subscribe(self, thread_id: str, callback: Callable[[Message], Any]) -> str:
        sub_id = uuid.uuid4().hex
        self.subscribers.setdefault(thread_id, []).append((sub_id, callback))
        return sub_id

    def unsubscribe(self, thread_id: str, sub_id: str) -> None:
        subs = self.subscribers.get(thread_id, [])
        self.subscribers[thread_id] = [(sid, cb) for sid, cb in subs if sid != sub_id]


def _get_bus():
    import os
    backend = os.getenv("CHAT_BUS_BACKEND", "memory").lower()
    if backend == "redis":
        try:
            from engines.chat.service.redis_transport import RedisBus
            host = os.getenv("REDIS_HOST", "localhost")
            port = int(os.getenv("REDIS_PORT", 6379))
            return RedisBus(host=host, port=port)
        except Exception as e:
            raise RuntimeError(f"Failed to load RedisBus: {e}")
            
    # If we get here, it's an invalid configuration
    if backend == "memory":
        # Explicitly disallow 'memory' as well, ensuring we only run with real infra
        raise RuntimeError("CHAT_BUS_BACKEND='memory' is not allowed in Real Infra mode.")
        
    raise RuntimeError(f"CHAT_BUS_BACKEND must be 'redis'. Got: '{backend}'")

class LazyBus:
    def __init__(self):
        self._impl = None

    @property
    def _bus(self):
        if self._impl is None:
            self._impl = _get_bus()
        return self._impl

    def __getattr__(self, name):
        return getattr(self._bus, name)

bus = LazyBus()


def _actor_type(role: str) -> ActorType:
    if role == "agent":
        return ActorType.AGENT
    if role == "system":
        return ActorType.SYSTEM
    return ActorType.HUMAN


def _message_to_stream_event(msg: Message, context: RequestContext) -> StreamEvent:
    return StreamEvent(
        type="chat_message",
        event_id=msg.id,
        ts=msg.created_at,
        ids=EventIds(
            request_id=context.request_id,
            run_id=msg.thread_id,
            step_id=msg.id,
        ),
        routing=RoutingKeys(
            tenant_id=context.tenant_id,
            env=context.env,
            mode=context.mode,
            project_id=context.project_id,
            app_id=context.app_id,
            surface_id=context.surface_id,
            thread_id=msg.thread_id,
            actor_id=msg.sender.id,
            actor_type=_actor_type(msg.role),
        ),
        data={
            "text": msg.text,
            "role": msg.role,
            "scope": msg.scope.dict(exclude_none=True) if msg.scope else None,
        },
        trace_id=context.request_id,
        meta=EventMeta(
            priority=EventPriority.INFO,
            persist=PersistPolicy.ALWAYS,
            last_event_id=msg.id,
        ),
    )


def publish_message(
    thread_id: str,
    sender: Contact,
    text: str,
    role: str = "user",
    scope: ChatScope | None = None,
    context: RequestContext | None = None,
) -> Message:
    if context is None:
        raise RuntimeError("RequestContext is required to publish a chat message")
    msg = Message(id=uuid.uuid4().hex, thread_id=thread_id, sender=sender, text=text, role=role, scope=scope)
    bus.add_message(thread_id, msg)
    get_timeline_store().append(thread_id, _message_to_stream_event(msg, context), context)
    return msg


async def subscribe_async(thread_id: str, last_event_id: str | None = None, context: RequestContext | None = None):
    queue: asyncio.Queue[Message] = asyncio.Queue()
    if context is None:
        raise RuntimeError("RequestContext is required for stream replay")

    # Durable replay
    timeline = get_timeline_store()
    replay_events = timeline.list_after(thread_id, after_event_id=last_event_id)
    for ev in replay_events:
        sender = Contact(id=ev.routing.actor_id)
        text = ev.data.get("text")
        if text is None:
            try:
                text = json.dumps(ev.data)
            except Exception:
                text = str(ev.data)
        msg = Message(
            id=ev.event_id,
            thread_id=thread_id,
            sender=sender,
            text=text,
            role=ev.data.get("role", "system"),
        )
        queue.put_nowait(msg)

    sub_id = bus.subscribe(thread_id, lambda msg: queue.put_nowait(msg))
    try:
        while True:
            msg = await queue.get()
            yield msg
    finally:
        bus.unsubscribe(thread_id, sub_id)
