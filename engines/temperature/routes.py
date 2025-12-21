from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from engines.common.identity import RequestContext, assert_context_matches, get_request_context
from engines.identity.auth import AuthContext, get_auth_context, require_tenant_membership, require_tenant_role
from engines.temperature.models import CeilingConfig, FloorConfig, TemperatureWeights
from engines.temperature.service import get_temperature_service
from engines.strategy_lock.service import get_strategy_lock_service

router = APIRouter(prefix="/temperature", tags=["temperature"])


@router.put("/floors")
def put_floors(cfg: FloorConfig, context: RequestContext = Depends(get_request_context), auth=Depends(get_auth_context)):
    assert_context_matches(context, cfg.tenant_id, cfg.env)
    require_tenant_role(auth, cfg.tenant_id, ["owner", "admin"])
    get_strategy_lock_service().require_strategy_lock_or_raise(context, cfg.surface, "temperature:upsert_floors")
    return get_temperature_service().upsert_floor(context, cfg)


@router.put("/ceilings")
def put_ceilings(cfg: CeilingConfig, context: RequestContext = Depends(get_request_context), auth=Depends(get_auth_context)):
    assert_context_matches(context, cfg.tenant_id, cfg.env)
    require_tenant_role(auth, cfg.tenant_id, ["owner", "admin"])
    get_strategy_lock_service().require_strategy_lock_or_raise(context, cfg.surface, "temperature:upsert_ceilings")
    return get_temperature_service().upsert_ceiling(context, cfg)


@router.put("/weights")
def put_weights(cfg: TemperatureWeights, context: RequestContext = Depends(get_request_context), auth=Depends(get_auth_context)):
    assert_context_matches(context, cfg.tenant_id, cfg.env)
    require_tenant_role(auth, cfg.tenant_id, ["owner", "admin"])
    get_strategy_lock_service().require_strategy_lock_or_raise(context, cfg.surface, "temperature:upsert_weights")
    return get_temperature_service().upsert_weights(context, cfg)


@router.get("/config")
def get_config(
    surface: str,
    context: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    return get_temperature_service().get_config_bundle(context, surface)


@router.get("/current")
def get_current_temperature(
    surface: str,
    window_days: int = Query(7, ge=1, le=90),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    if context.tenant_id not in auth.tenant_ids:
        raise HTTPException(status_code=403, detail="tenant mismatch")
    return get_temperature_service().compute_temperature(context, surface, window_days)


@router.get("/history")
def get_history(
    surface: str,
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    if context.tenant_id not in auth.tenant_ids:
        raise HTTPException(status_code=403, detail="tenant mismatch")
    snaps = get_temperature_service().repo.list_snapshots(context.tenant_id, context.env, surface, limit, offset)
    return {"items": snaps}
