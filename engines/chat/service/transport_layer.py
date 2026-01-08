"""Durable chat transport backed by routed chat_store."""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, Callable, Dict, List, Tuple

from engines.chat.contracts import Message, Thread, Contact, ChatScope
from engines.common.identity import RequestContext
from engines.chat.store_service import chat_store_or_503
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
        self.messages: Dict[str, List[Message]] = {}
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
        self.messages.setdefault(thread_id, []).append(msg)
        for _, callback in self.subscribers.get(thread_id, []):
            try:
                callback(msg)
            except Exception:
                pass

    def get_messages(self, thread_id: str, after_id: str | None = None) -> List[Message]:
        msgs = self.messages.get(thread_id, [])
        if not after_id:
            return msgs
        try:
            for i, m in enumerate(msgs):
                if m.id == after_id:
                    return msgs[i + 1 :]
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
    if backend == "memory":
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
    store = chat_store_or_503(context)
    record = store.append_message(thread_id=thread_id, text=text, role=role, sender_id=sender.id)
    msg = Message(
        id=record.message_id,
        thread_id=thread_id,
        sender=sender,
        text=text,
        role=role,
        scope=scope,
        created_at=record.timestamp,
    )
    try:
        bus.add_message(thread_id, msg)
    except Exception:
        # Bus is observational only; ignore if unavailable
        pass
    try:
        get_timeline_store().append(thread_id, _message_to_stream_event(msg, context), context)
    except Exception:
        # Timeline is observational; do not block writes
        pass
    return msg


async def subscribe_async(thread_id: str, last_event_id: str | None = None, context: RequestContext | None = None):
    if context is None:
        raise RuntimeError("RequestContext is required for stream replay")
    store = chat_store_or_503(context)
    cursor = last_event_id
    poll_interval = 0.25
    sub_id: str | None = None
    queue: asyncio.Queue[Message] = asyncio.Queue()
    try:
        sub_id = bus.subscribe(thread_id, lambda m: queue.put_nowait(m))
    except Exception:
        sub_id = None
    try:
        while True:
            messages = store.list_messages(thread_id=thread_id, after_cursor=cursor, limit=100)
            if messages:
                for rec in messages:
                    cursor = rec.cursor
                    yield Message(
                        id=rec.message_id,
                        thread_id=thread_id,
                        sender=Contact(id=rec.sender_id),
                        text=rec.text,
                        role=rec.role,
                    )
            try:
                msg = queue.get_nowait()
                yield msg
                cursor = msg.id
            except asyncio.QueueEmpty:
                await asyncio.sleep(poll_interval)
            except Exception:
                await asyncio.sleep(poll_interval)
    finally:
        if sub_id:
            try:
                bus.unsubscribe(thread_id, sub_id)
            except Exception:
                pass
