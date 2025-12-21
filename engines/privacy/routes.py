from __future__ import annotations

from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from engines.common.identity import RequestContext, assert_context_matches, get_request_context
from engines.identity.auth import AuthContext, get_auth_context, require_tenant_membership, require_tenant_role
from engines.privacy.train_prefs import get_training_pref_service, TrainingPreferenceService

router = APIRouter(prefix="/privacy/train-prefs", tags=["privacy"])


class TenantOptOutRequest(BaseModel):
    opt_out: bool
    tenant_id: Optional[str] = None
    env: Optional[str] = None


class UserOptOutRequest(BaseModel):
    user_id: str
    opt_out: bool
    tenant_id: Optional[str] = None
    env: Optional[str] = None


def _ensure_membership(auth: AuthContext, ctx: RequestContext) -> None:
    require_tenant_membership(auth, ctx.tenant_id)
    require_tenant_role(auth, ctx.tenant_id, ["owner", "admin", "member"])


@router.post("/tenant")
def set_tenant_opt_out(
    payload: TenantOptOutRequest,
    ctx: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    _ensure_membership(auth, ctx)
    assert_context_matches(ctx, payload.tenant_id, payload.env)
    svc = get_training_pref_service()
    pref = svc.set_tenant_opt_out(ctx.tenant_id, ctx.env, payload.opt_out)
    return asdict(pref)


@router.post("/user")
def set_user_opt_out(
    payload: UserOptOutRequest,
    ctx: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    _ensure_membership(auth, ctx)
    assert_context_matches(ctx, payload.tenant_id, payload.env)
    if not ctx.user_id or payload.user_id != ctx.user_id:
        raise HTTPException(status_code=403, detail="user_id mismatch")
    svc = get_training_pref_service()
    pref = svc.set_user_opt_out(ctx.tenant_id, ctx.env, payload.user_id, payload.opt_out)
    return asdict(pref)


@router.get("")
def get_preferences(
    user_id: Optional[str] = Query(default=None),
    ctx: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    require_tenant_membership(auth, ctx.tenant_id)
    if user_id and ctx.user_id and user_id != ctx.user_id:
        raise HTTPException(status_code=403, detail="user_id mismatch")
    svc = get_training_pref_service()
    prefs = svc.prefs_snapshot(ctx.tenant_id, ctx.env)
    filtered = [asdict(pref) for pref in prefs if not user_id or pref.user_id == user_id]
    train_ok = svc.train_ok(ctx.tenant_id, ctx.env, user_id or ctx.user_id)
    return {
        "tenant_id": ctx.tenant_id,
        "env": ctx.env,
        "train_ok": train_ok,
        "preferences": filtered,
    }
