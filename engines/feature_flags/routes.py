from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from engines.common.error_envelope import error_response
from engines.common.identity import RequestContext, get_request_context
from engines.feature_flags.models import FeatureFlags
from engines.feature_flags.service import get_feature_flags, update_feature_flags
from engines.identity.auth import AuthContext, get_auth_context, require_tenant_role
from engines.nexus.hardening.gate_chain import GateChain, get_gate_chain

router = APIRouter(prefix="/feature-flags", tags=["feature-flags"])


@router.get("", response_model=FeatureFlags)
def get_flags(
    ctx: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(get_auth_context),
):
    # Ensure user has access to tenancy
    require_tenant_role(auth, ctx.tenant_id, ["owner", "admin", "member", "viewer"])
    try:
        return get_feature_flags(ctx.tenant_id, ctx.env)
    except HTTPException:
        raise
    except Exception as exc:
        return error_response(code="flags.get_failed", message=str(exc), status_code=500)


@router.put("", response_model=FeatureFlags)
def set_flags(
    flags: FeatureFlags,
    ctx: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(get_auth_context),
    gate_chain: GateChain = Depends(get_gate_chain),
):
    # Only owners/admins can change flags
    require_tenant_role(auth, ctx.tenant_id, ["owner", "admin"])
    
    try:
        gate_chain.run(ctx, action="flags_update", surface="flags", subject_type="feature_flags")
        
        # Force alignment with context to prevent spoofing
        flags.tenant_id = ctx.tenant_id
        flags.env = ctx.env
        return update_feature_flags(flags)
    except HTTPException:
        raise
    except Exception as exc:
        return error_response(code="flags.update_failed", message=str(exc), status_code=500)
