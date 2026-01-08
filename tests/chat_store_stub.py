from __future__ import annotations

import uuid
from datetime import datetime
import importlib
import sys
from typing import Dict, List, Optional

from engines.chat.store_service import ChatMessageRecord
from engines.common.error_envelope import cursor_invalid_error


class InMemoryChatStore:
    """Lightweight chat store mock used by SSE/canvas tests."""

    def __init__(self) -> None:
        self._events: Dict[str, List[ChatMessageRecord]] = {}

    def append_message(
        self, thread_id: str, text: str, role: str, sender_id: str
    ) -> ChatMessageRecord:
        event_id = uuid.uuid4().hex
        timestamp = datetime.utcnow().isoformat()
        record = ChatMessageRecord(
            message_id=event_id,
            thread_id=thread_id,
            text=text,
            role=role,
            sender_id=sender_id,
            cursor=event_id,
            timestamp=timestamp,
        )
        self._events.setdefault(thread_id, []).append(record)
        return record

    def list_messages(
        self, thread_id: str, after_cursor: Optional[str] = None, limit: int = 100
    ) -> List[ChatMessageRecord]:
        events = self._events.get(thread_id, [])
        if after_cursor:
            for idx, record in enumerate(events):
                if record.cursor == after_cursor:
                    start = idx + 1
                    break
            else:
                raise cursor_invalid_error(after_cursor, domain="chat")
        else:
            start = 0
        return events[start : start + limit]

    def latest_cursor(self, thread_id: str) -> Optional[str]:
        events = self._events.get(thread_id, [])
        if not events:
            return None
        return events[-1].cursor


def install_chat_store_stub(monkeypatch, targets=None) -> InMemoryChatStore:
    if targets is None:
        targets = [
            "engines.chat.service.transport_layer.chat_store_or_503",
            "engines.chat.service.sse_transport.chat_store_or_503",
            "engines.chat.service.routes.chat_store_or_503",
            "engines.canvas_stream.router.chat_store_or_503",
            "engines.chat.store_service.chat_store_or_503",
        ]
    store = InMemoryChatStore()
    for target in targets:
        module_name, _, attr = target.rpartition(".")
        if not module_name or not attr:
            raise ValueError(f"invalid target path: {target}")
        module = sys.modules.get(module_name)
        if module is None:
            module = importlib.import_module(module_name)
        monkeypatch.setattr(module, attr, lambda ctx, store=store: store)
    return store
