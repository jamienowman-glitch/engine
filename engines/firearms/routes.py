from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from engines.common.identity import RequestContext, assert_context_matches, get_request_context
from engines.firearms.models import FirearmsLicence, LicenceLevel, LicenceStatus
from engines.firearms.service import FirearmsService, get_firearms_service
from engines.identity.auth import get_auth_context, require_tenant_membership, require_tenant_role

router = APIRouter(prefix="/firearms/licences", tags=["firearms"])


@router.post("", response_model=FirearmsLicence)
def issue_licence(
    payload: FirearmsLicence,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    assert_context_matches(context, payload.tenant_id, payload.env)
    require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    return get_firearms_service().issue_licence(context, payload)


@router.patch("/{licence_id}", response_model=FirearmsLicence)
def revoke_licence(
    licence_id: str = Path(...),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    return get_firearms_service().revoke_licence(context, licence_id)


@router.get("/{licence_id}", response_model=FirearmsLicence)
def get_licence(
    licence_id: str = Path(...),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    return get_firearms_service().get_licence(context, licence_id)


@router.get("", response_model=list[FirearmsLicence])
def list_licences(
    subject_type: Optional[str] = Query(default=None),
    subject_id: Optional[str] = Query(default=None),
    status: Optional[LicenceStatus] = Query(default=None),
    level: Optional[LicenceLevel] = Query(default=None),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    return get_firearms_service().list_licences(context, subject_type=subject_type, subject_id=subject_id, status=status, level=level)


@router.get("/check/{subject_type}/{subject_id}")
def check_action(
    subject_type: str,
    subject_id: str,
    action: str = Query(...),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    svc = get_firearms_service()
    allowed = svc.check_licence_allowed(context.tenant_id, context.env, subject_type, subject_id, action)
    return {"allowed": allowed}


@router.post("/dangerous-demo/{subject_type}/{subject_id}")
def dangerous_demo(
    subject_type: str,
    subject_id: str,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    get_firearms_service().require_licence_or_raise(context, subject_type=subject_type, subject_id=subject_id, action="dangerous_tool_use")
    return {"status": "allowed"}
