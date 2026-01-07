"""Chat rail HTTP endpoints (chat_store-backed)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional

from engines.chat.contracts import Contact
from engines.chat.service.transport_layer import publish_message
from engines.chat.store_service import chat_store_or_503, MissingChatStoreRoute
from engines.common.error_envelope import error_response, missing_route_error, cursor_invalid_error
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context, require_tenant_membership
from engines.nexus.hardening.gate_chain import GateChain, get_gate_chain

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatAppendRequest(BaseModel):
    text: str
    role: str = Field(default="user")


class ChatMessageOut(BaseModel):
    id: str
    text: str
    role: str
    sender_id: str
    cursor: str
    timestamp: str


class ChatListResponse(BaseModel):
    messages: List[ChatMessageOut]
    cursor: Optional[str] = None


class ChatSnapshotResponse(BaseModel):
    cursor: Optional[str]
    count: int


def _ensure_membership(auth: AuthContext, context: RequestContext, resource_kind: str = "chat_store") -> None:
    try:
        require_tenant_membership(auth, context.tenant_id)
    except HTTPException as exc:
        error_response(
            code="auth.tenant_membership_required",
            message=str(exc.detail),
            status_code=exc.status_code,
            resource_kind=resource_kind,
        )


@router.post("/threads/{thread_id}/messages", response_model=ChatMessageOut)
def append_message(
    thread_id: str,
    payload: ChatAppendRequest,
    context: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(get_auth_context),
    gate_chain: GateChain = Depends(get_gate_chain),
):
    # Enforce GateChain
    try:
        gate_chain.run(ctx=context, action="chat_message_append", resource_kind="chat_thread")
    except HTTPException as exc:
        raise exc

    if auth.default_tenant_id != context.tenant_id:
        error_response(
            code="auth.tenant_mismatch",
            message="Tenant mismatch",
            status_code=403,
            resource_kind="chat_store",
        )
    _ensure_membership(auth, context)
    sender = Contact(id=auth.user_id)
    try:
        msg = publish_message(thread_id=thread_id, sender=sender, text=payload.text, role=payload.role, context=context)
        return ChatMessageOut(
            id=msg.id,
            text=msg.text,
            role=msg.role,
            sender_id=msg.sender.id,
            cursor=msg.id,
            timestamp=str(msg.created_at),
        )
    except HTTPException:
        raise
    except MissingChatStoreRoute as exc:
        missing_route_error(
            resource_kind="chat_store",
            tenant_id=context.tenant_id,
            env=context.env,
            status_code=exc.status_code,
        )
    except Exception as exc:
        error_response(
            code="chat.append_failed",
            message=str(exc),
            status_code=500,
            resource_kind="chat_store",
        )


@router.get("/threads/{thread_id}/messages", response_model=ChatListResponse)
def list_messages(
    thread_id: str,
    cursor: Optional[str] = Query(None, alias="cursor"),
    limit: int = Query(100, ge=1, le=500),
    context: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(get_auth_context),
):
    if auth.default_tenant_id != context.tenant_id:
        error_response(
            code="auth.tenant_mismatch",
            message="Tenant mismatch",
            status_code=403,
            resource_kind="chat_store",
        )
    _ensure_membership(auth, context)
    try:
        store = chat_store_or_503(context)
        messages = store.list_messages(thread_id=thread_id, after_cursor=cursor, limit=limit)
        last_cursor = messages[-1].cursor if messages else cursor
        return ChatListResponse(
            messages=[
                ChatMessageOut(
                    id=m.message_id,
                    text=m.text,
                    role=m.role,
                    sender_id=m.sender_id,
                    cursor=m.cursor,
                    timestamp=m.timestamp,
                )
                for m in messages
            ],
            cursor=last_cursor,
        )
    except HTTPException:
        raise
    except MissingChatStoreRoute as exc:
        missing_route_error(
            resource_kind="chat_store",
            tenant_id=context.tenant_id,
            env=context.env,
            status_code=exc.status_code,
        )
    except Exception as exc:
        error_response(
            code="chat.list_failed",
            message=str(exc),
            status_code=500,
            resource_kind="chat_store",
        )


@router.get("/threads/{thread_id}/snapshot", response_model=ChatSnapshotResponse)
def snapshot(
    thread_id: str,
    context: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(get_auth_context),
):
    if auth.default_tenant_id != context.tenant_id:
        error_response(
            code="auth.tenant_mismatch",
            message="Tenant mismatch",
            status_code=403,
            resource_kind="chat_store",
        )
    _ensure_membership(auth, context)
    try:
        store = chat_store_or_503(context)
        cursor = store.latest_cursor(thread_id)
        return ChatSnapshotResponse(cursor=cursor, count=len(store.list_messages(thread_id, after_cursor=None, limit=1000)))
    except HTTPException:
        raise
    except MissingChatStoreRoute as exc:
        missing_route_error(
            resource_kind="chat_store",
            tenant_id=context.tenant_id,
            env=context.env,
            status_code=exc.status_code,
        )
    except Exception as exc:
        error_response(
            code="chat.snapshot_failed",
            message=str(exc),
            status_code=500,
            resource_kind="chat_store",
        )
