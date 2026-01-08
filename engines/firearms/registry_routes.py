from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from engines.common.identity import RequestContext, get_request_context
from engines.common.error_envelope import error_response
from engines.identity.auth import get_auth_context, require_tenant_membership, require_tenant_role
from engines.firearms.models import Firearm
from engines.firearms.service import FirearmsService, get_firearms_service

router = APIRouter(prefix="/registry/firearms", tags=["firearms-registry"])

@router.get("/license-types", response_model=List[Firearm])
def list_license_types(
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
    service: FirearmsService = Depends(get_firearms_service),
) -> List[Firearm]:
    require_tenant_membership(auth, context.tenant_id)
    try:
        return service.list_firearms(context)
    except Exception as exc:
        error_response(
            code="firearms.registry_read_failed",
            message=str(exc),
            status_code=500,
            resource_kind="firearms_registry",
        )

@router.post("/license-types", response_model=Firearm)
def create_license_type(
    payload: Firearm,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
    service: FirearmsService = Depends(get_firearms_service),
) -> Firearm:
    # Only admins/owners should define new license types
    require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    try:
        return service.register_firearm(context, payload)
    except Exception as exc:
        error_response(
            code="firearms.registry_write_failed",
            message=str(exc),
            status_code=500,
            resource_kind="firearms_registry",
        )

@router.get("/inspect")
def inspect_policy(
    tool_id: str,
    scope_name: str,
    context: RequestContext = Depends(get_request_context),
    service: FirearmsService = Depends(get_firearms_service),
) -> dict:
    # 1. Construct action key
    action_name = f"{tool_id}.{scope_name}"
    
    # 2. Check binding (direct repo access for raw policy)
    binding = service.repo.get_binding(context, action_name)
    
    requires_firearms = False
    details = {}
    
    if binding:
        requires_firearms = True
        details = {
            "firearm_id": binding.firearm_id,
            "strategy_lock_required": binding.strategy_lock_required
        }
        
    return {
        "tool_id": tool_id,
        "scope_name": scope_name,
        "requires_firearms": requires_firearms,
        "details": details
    }
