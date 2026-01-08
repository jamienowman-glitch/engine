from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from engines.common.identity import RequestContext, get_request_context
from engines.common.error_envelope import error_response
from engines.identity.auth import get_auth_context, require_tenant_membership
from engines.firearms.models import FirearmBinding, FirearmGrant
from engines.firearms.service import get_firearms_service, FirearmsService

router = APIRouter(prefix="/firearms", tags=["firearms"])


class FirearmPolicyPayload(BaseModel):
    bindings: List[FirearmBinding]


class FirearmGrantsPayload(BaseModel):
    grants: List[FirearmGrant]


def _ensure_membership(context: RequestContext, auth) -> None:
    try:
        require_tenant_membership(auth, context.tenant_id)
    except HTTPException as exc:
        error_response(
            code="auth.tenant_membership_required",
            message=str(exc.detail),
            status_code=exc.status_code,
            resource_kind="firearms_policy_store",
        )


@router.get("/policy", response_model=List[FirearmBinding])
def get_policy(
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
    service: FirearmsService = Depends(get_firearms_service),
) -> List[FirearmBinding]:
    _ensure_membership(context, auth)
    try:
        return service.repo.list_bindings(context)
    except HTTPException:
        raise
    except Exception as exc:
        error_response(
            code="firearms.policy_read_failed",
            message=str(exc),
            status_code=500,
            resource_kind="firearms_policy_store",
        )


@router.put("/policy", response_model=List[FirearmBinding])
def put_policy(
    payload: FirearmPolicyPayload,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
    service: FirearmsService = Depends(get_firearms_service),
) -> List[FirearmBinding]:
    _ensure_membership(context, auth)
    try:
        saved = []
        for binding in payload.bindings:
            saved.append(service.bind_action(context, binding))
        return saved
    except HTTPException:
        raise
    except Exception as exc:
        error_response(
            code="firearms.policy_write_failed",
            message=str(exc),
            status_code=500,
            resource_kind="firearms_policy_store",
        )


@router.get("/grants", response_model=List[FirearmGrant])
def list_grants(
    agent_id: Optional[str] = None,
    user_id: Optional[str] = None,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
    service: FirearmsService = Depends(get_firearms_service),
) -> List[FirearmGrant]:
    _ensure_membership(context, auth)
    try:
        target_user_id = user_id or (None if agent_id else context.user_id)
        return service.repo.list_grants(context, agent_id=agent_id, user_id=target_user_id)
    except HTTPException:
        raise
    except Exception as exc:
        error_response(
            code="firearms.grants_read_failed",
            message=str(exc),
            status_code=500,
            resource_kind="firearms_policy_store",
        )


@router.put("/grants", response_model=List[FirearmGrant])
def put_grants(
    payload: FirearmGrantsPayload,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
    service: FirearmsService = Depends(get_firearms_service),
) -> List[FirearmGrant]:
    _ensure_membership(context, auth)
    saved: List[FirearmGrant] = []
    try:
        for grant in payload.grants:
            grant.tenant_id = context.tenant_id
            saved.append(service.grant_licence(context, grant))
        return saved
    except HTTPException:
        raise
    except Exception as exc:
        error_response(
            code="firearms.grants_write_failed",
            message=str(exc),
            status_code=500,
            resource_kind="firearms_policy_store",
        )
