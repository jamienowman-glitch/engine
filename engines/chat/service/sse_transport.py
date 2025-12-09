"""SSE transport wired to chat pipeline."""
from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from engines.chat.contracts import Contact
from engines.chat.pipeline import process_message
from engines.chat.service.transport_layer import subscribe_async

router = APIRouter()


async def event_stream(thread_id: str) -> AsyncGenerator[str, None]:
    async for msg in subscribe_async(thread_id):
        payload = json.dumps({"event": "message", "data": msg.dict()}, default=str)
        yield f"event: message\ndata: {payload}\n\n"
        await asyncio.sleep(0)


@router.get("/sse/chat/{thread_id}")
async def sse_chat(thread_id: str) -> StreamingResponse:
    return StreamingResponse(event_stream(thread_id), media_type="text/event-stream")


@router.post("/sse/chat/{thread_id}")
async def post_message(thread_id: str, sender: Contact, text: str):
    msgs = process_message(thread_id, sender, text)
    return {"posted": [m.dict() for m in msgs]}
