from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from engines.common.identity import RequestContext, assert_context_matches, get_request_context
from engines.identity.analytics_service import get_analytics_service
from engines.identity.auth import get_auth_context, require_tenant_membership, require_tenant_role
from engines.identity.models import TenantAnalyticsConfig
from engines.strategy_lock.service import get_strategy_lock_service

router = APIRouter(prefix="/tenants", tags=["analytics"])


@router.put("/{tenant_id}/analytics/config", response_model=TenantAnalyticsConfig)
def put_analytics_config(
    tenant_id: str = Path(...),
    payload: TenantAnalyticsConfig = None,  # type: ignore[assignment]
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    if payload is None:
        raise HTTPException(status_code=400, detail="payload required")
    if tenant_id != payload.tenant_id:
        raise HTTPException(status_code=400, detail="tenant mismatch in payload")
    assert_context_matches(context, payload.tenant_id, payload.env)
    require_tenant_role(auth, tenant_id, ["owner", "admin"])
    get_strategy_lock_service().require_strategy_lock_or_raise(context, payload.surface if hasattr(payload, "surface") else None, "analytics:config_upsert")
    svc = get_analytics_service()
    return svc.upsert_config(payload)


@router.get("/{tenant_id}/analytics/config", response_model=list[TenantAnalyticsConfig])
def list_analytics_configs(
    tenant_id: str = Path(...),
    env: Optional[str] = Query(default=None),
    surface: Optional[str] = Query(default=None),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    assert_context_matches(context, tenant_id, env)
    require_tenant_membership(auth, tenant_id)
    return get_analytics_service().list_configs(tenant_id, env, surface)


@router.get("/{tenant_id}/analytics/config/current", response_model=TenantAnalyticsConfig | None)
def current_analytics_config(
    tenant_id: str = Path(...),
    env: str = Query(...),
    surface: str = Query(...),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    assert_context_matches(context, tenant_id, env)
    require_tenant_membership(auth, tenant_id)
    cfg = get_analytics_service().resolve_effective(tenant_id, env, surface)
    if not cfg:
        raise HTTPException(status_code=404, detail="analytics config not found")
    return cfg
