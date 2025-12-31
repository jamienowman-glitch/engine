"""HTTP transport wired to chat pipeline."""
from __future__ import annotations

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel

from engines.chat.contracts import Contact, ChatScope
from engines.chat.pipeline import process_message
from engines.chat.service.transport_layer import bus
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context, require_tenant_membership
from engines.nexus.hardening.gate_chain import get_gate_chain

app = FastAPI(title="Chat HTTP Transport", version="0.2.0")


def _ensure_tenant_membership(ctx: RequestContext, auth: AuthContext) -> None:
    require_tenant_membership(auth, ctx.tenant_id)


@app.get("/chat/threads")
def list_threads(
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _ensure_tenant_membership(request_context, auth_context)
    return bus.list_threads()


@app.post("/chat/threads")
def create_thread(
    participants: list[Contact] = None,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _ensure_tenant_membership(request_context, auth_context)
    participants = participants or []
    thread = bus.create_thread(participants)
    # L1-T1: Auto-register thread for realtime access verification
    from engines.realtime.isolation import register_thread_resource
    register_thread_resource(request_context.tenant_id, thread.id)
    return thread


@app.get("/chat/threads/{thread_id}/messages")
def get_messages(
    thread_id: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _ensure_tenant_membership(request_context, auth_context)
    return bus.get_messages(thread_id)


class MessagePayload(BaseModel):
    sender: Contact
    text: str
    scope: ChatScope | None = None


@app.post("/chat/threads/{thread_id}/messages")
async def post_message(
    thread_id: str,
    payload: MessagePayload,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    _ensure_tenant_membership(request_context, auth_context)
    
    # Lane 2: Call GateChain before processing message
    try:
        gate_chain = get_gate_chain()
        gate_chain.run(
            ctx=request_context,
            action="chat_send",
            surface=request_context.surface_id or "chat",
            subject_type="thread",
            subject_id=thread_id,
        )
    except HTTPException as exc:
        raise exc
    
    msgs = await process_message(
        thread_id,
        payload.sender,
        payload.text,
        scope=payload.scope,
        context=request_context,
    )
    return {"posted": [m.dict() for m in msgs]}


def create_app() -> FastAPI:
    return app
