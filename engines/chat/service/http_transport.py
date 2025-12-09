"""HTTP transport wired to chat pipeline."""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from engines.chat.contracts import Contact, ChatScope
from engines.chat.pipeline import process_message
from engines.chat.service.transport_layer import bus

app = FastAPI(title="Chat HTTP Transport", version="0.2.0")


@app.get("/chat/threads")
def list_threads():
    return bus.list_threads()


@app.post("/chat/threads")
def create_thread(participants: list[Contact] = None):
    participants = participants or []
    thread = bus.create_thread(participants)
    return thread


@app.get("/chat/threads/{thread_id}/messages")
def get_messages(thread_id: str):
    return bus.get_messages(thread_id)


class MessagePayload(BaseModel):
    sender: Contact
    text: str
    scope: ChatScope | None = None


@app.post("/chat/threads/{thread_id}/messages")
def post_message(thread_id: str, payload: MessagePayload):
    msgs = process_message(thread_id, payload.sender, payload.text, scope=payload.scope)
    return {"posted": [m.dict() for m in msgs]}


def create_app() -> FastAPI:
    return app
