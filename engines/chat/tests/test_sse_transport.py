"""Tests focused on the SSE stream event generation without spinning up HTTP streaming."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Dict, Union

from engines.chat.contracts import Contact, Message
from engines.chat.service.sse_transport import event_stream
from engines.chat.service.transport_layer import bus
from engines.common.identity import RequestContext
from engines.realtime.isolation import register_thread_resource


def _line_to_text(line: Union[bytes, str]) -> str:
    if isinstance(line, bytes):
        return line.decode("utf-8", errors="ignore")
    return str(line)


def _parse_sse_chunk(chunk: str) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    for raw in chunk.splitlines():
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        parsed[key.strip()] = value.strip()
    return parsed


async def _collect_event_chunk(thread_id: str, ctx: RequestContext) -> str:
    stream = event_stream(thread_id, ctx)
    task = asyncio.create_task(stream.__anext__())
    await asyncio.sleep(0)
    bus.add_message(
        thread_id,
        Message(
            id="evt-sse-1",
            thread_id=thread_id,
            sender=Contact(id=ctx.user_id or "test"),
            text="hello sse",
            role="user",
            created_at=datetime.utcnow(),
        ),
    )
    chunk = await task
    await stream.aclose()
    return chunk


def test_event_stream_includes_trace() -> None:
    thread_id = "thread-sse-clean"
    ctx = RequestContext(tenant_id="t_demo", env="dev", request_id="trace-sse-1", user_id="u_test")
    register_thread_resource(ctx.tenant_id, thread_id)

    chunk = asyncio.run(_collect_event_chunk(thread_id, ctx))
    event = _parse_sse_chunk(_line_to_text(chunk))
    assert event["event"] == "user_message"
    payload = json.loads(event["data"])
    assert payload["trace_id"] == ctx.request_id
    assert payload["routing"]["tenant_id"] == ctx.tenant_id
    assert payload["routing"]["env"] == ctx.env
