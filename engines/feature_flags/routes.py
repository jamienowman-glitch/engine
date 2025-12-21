from __future__ import annotations

from fastapi import APIRouter, Depends

from engines.common.identity import RequestContext, get_request_context
from engines.feature_flags.models import FeatureFlags
from engines.feature_flags.service import get_feature_flags, update_feature_flags
from engines.identity.auth import AuthContext, get_auth_context, require_tenant_role

router = APIRouter(prefix="/feature-flags", tags=["feature-flags"])


@router.get("", response_model=FeatureFlags)
def get_flags(
    ctx: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(get_auth_context),
):
    # Ensure user has access to tenancy
    require_tenant_role(auth, ctx.tenant_id, ["owner", "admin", "member", "viewer"])
    return get_feature_flags(ctx.tenant_id, ctx.env)


@router.put("", response_model=FeatureFlags)
def set_flags(
    flags: FeatureFlags,
    ctx: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(get_auth_context),
):
    # Only owners/admins can change flags
    require_tenant_role(auth, ctx.tenant_id, ["owner", "admin"])
    # Force alignment with context to prevent spoofing
    flags.tenant_id = ctx.tenant_id
    flags.env = ctx.env
    return update_feature_flags(flags)
