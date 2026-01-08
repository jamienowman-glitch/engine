"""HTTP transport wired to chat pipeline."""
from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from engines.chat.contracts import Contact, ChatScope
from engines.chat.pipeline import process_message
from engines.chat.service.transport_layer import bus
from engines.common.error_envelope import ErrorDetail, ErrorEnvelope, build_error_envelope
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context, require_tenant_membership
from engines.nexus.hardening.gate_chain import get_gate_chain

logger = logging.getLogger(__name__)

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


def _normalize_existing_envelope(detail: Any, status_code: int) -> ErrorEnvelope | None:
    """Return an ErrorEnvelope if the detail already carries a canonical structure."""
    payload: Dict[str, Any] | None = None
    if isinstance(detail, ErrorEnvelope):
        payload = detail.model_dump()["error"]
    elif isinstance(detail, dict):
        maybe_error = detail.get("error")
        if isinstance(maybe_error, dict):
            payload = maybe_error

    if payload is None:
        return None

    normalized = dict(payload)
    normalized["http_status"] = status_code
    try:
        return ErrorEnvelope(error=ErrorDetail.model_validate(normalized))
    except ValidationError:
        logger.debug("Rejecting malformed error envelope payload %s", payload, exc_info=True)
        return None


async def _http_exception_handler(request: Request, exc: HTTPException):
    envelope = _normalize_existing_envelope(exc.detail, exc.status_code)
    if envelope is None:
        message = exc.detail if isinstance(exc.detail, str) else "HTTP exception"
        details: Dict[str, Any] | None = {"original_detail": str(exc.detail)} if exc.detail else None
        envelope = build_error_envelope(
            code="http.exception",
            message=str(message),
            status_code=exc.status_code,
            details=details,
        )
    return JSONResponse(content=envelope.model_dump(), status_code=exc.status_code)


async def _validation_exception_handler(request: Request, exc: RequestValidationError):
# NB: Validation errors should always carry a 400 http_status.
    envelope = build_error_envelope(
        code="validation.error",
        message="Validation failed",
        status_code=400,
        details={"errors": exc.errors()},
    )
    return JSONResponse(content=envelope.model_dump(), status_code=400)


async def _generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception while processing %s %s", request.method, request.url)
    envelope = build_error_envelope(
        code="internal.error",
        message="Internal server error",
        status_code=500,
    )
    return JSONResponse(content=envelope.model_dump(), status_code=500)


def register_error_handlers(target_app: FastAPI) -> None:
    """Attach canonical error handlers to the passed FastAPI app."""
    if getattr(target_app.state, "northstar_error_handlers", False):
        return
    target_app.add_exception_handler(HTTPException, _http_exception_handler)
    target_app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    target_app.add_exception_handler(Exception, _generic_exception_handler)
    target_app.state.northstar_error_handlers = True


register_error_handlers(app)


def create_app() -> FastAPI:
    return app
