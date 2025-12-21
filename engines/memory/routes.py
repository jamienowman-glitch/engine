from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Path

from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import get_auth_context, require_tenant_membership
from engines.memory.models import Blackboard, MessageRecord
from engines.memory.service import get_memory_service

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("/session/messages")
def append_message(
    session_id: str,
    message: MessageRecord,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    return get_memory_service().append_message(context, session_id, message)


@router.get("/session/messages")
def get_session_messages(
    session_id: str,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    return get_memory_service().get_session_memory(context, session_id)


@router.put("/blackboards/{key}")
def write_blackboard(
    key: str = Path(...),
    payload: Blackboard = None,  # type: ignore[assignment]
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    return get_memory_service().write_blackboard(context, key, payload)


@router.get("/blackboards/{key}")
def read_blackboard(
    key: str,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    return get_memory_service().read_blackboard(context, key)


@router.delete("/blackboards/{key}")
def delete_blackboard(
    key: str,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    get_memory_service().clear_blackboard(context, key)
    return {"status": "deleted"}
