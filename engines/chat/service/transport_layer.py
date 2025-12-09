"""In-memory pub/sub for chat transports (PLAN-024 stubs)."""
from __future__ import annotations

import asyncio
import uuid
from typing import Any, Callable, Dict, List, Tuple

from engines.chat.contracts import Message, Thread, Contact, ChatScope


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
        if thread_id not in self.messages:
            self.messages[thread_id] = []
        self.messages[thread_id].append(msg)
        for _, callback in self.subscribers.get(thread_id, []):
            callback(msg)

    def get_messages(self, thread_id: str) -> List[Message]:
        return self.messages.get(thread_id, [])

    def subscribe(self, thread_id: str, callback: Callable[[Message], Any]) -> str:
        sub_id = uuid.uuid4().hex
        self.subscribers.setdefault(thread_id, []).append((sub_id, callback))
        return sub_id

    def unsubscribe(self, thread_id: str, sub_id: str) -> None:
        subs = self.subscribers.get(thread_id, [])
        self.subscribers[thread_id] = [(sid, cb) for sid, cb in subs if sid != sub_id]


bus = InMemoryBus()


def publish_message(thread_id: str, sender: Contact, text: str, role: str = "user", scope: ChatScope | None = None) -> Message:
    msg = Message(id=uuid.uuid4().hex, thread_id=thread_id, sender=sender, text=text, role=role, scope=scope)
    bus.add_message(thread_id, msg)
    return msg


async def subscribe_async(thread_id: str):
    queue: asyncio.Queue[Message] = asyncio.Queue()
    sub_id = bus.subscribe(thread_id, lambda msg: queue.put_nowait(msg))
    try:
        while True:
            msg = await queue.get()
            yield msg
    finally:
        bus.unsubscribe(thread_id, sub_id)
