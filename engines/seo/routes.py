from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from engines.common.identity import RequestContext, assert_context_matches, get_request_context
from engines.identity.auth import get_auth_context, require_tenant_membership, require_tenant_role
from engines.seo.models import PageSeoConfig
from engines.seo.service import get_seo_service
from engines.strategy_lock.service import get_strategy_lock_service

router = APIRouter(prefix="/seo/pages", tags=["seo"])


@router.put("")
def upsert_page_seo(
    payload: PageSeoConfig,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    assert_context_matches(context, payload.tenant_id, payload.env)
    get_strategy_lock_service().require_strategy_lock_or_raise(context, payload.surface, "seo_page_config_update")
    return get_seo_service().upsert(context, payload)


@router.get("")
def list_page_seo(
    surface: Optional[str] = None,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    return get_seo_service().list(context, surface=surface)


@router.get("/{surface}/{page_type}")
def get_page_seo(
    surface: str,
    page_type: str,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    cfg = get_seo_service().get(context, surface, page_type)
    return cfg or {}
