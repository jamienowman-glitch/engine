from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from engines.budget.models import UsageEvent
from engines.budget.service import BudgetService, get_budget_service
from engines.common.identity import RequestContext, assert_context_matches, get_request_context
from engines.identity.auth import get_auth_context, require_tenant_membership

router = APIRouter(prefix="/budget/usage", tags=["budget"])


@router.post("")
def post_usage(
    payload: List[UsageEvent] | UsageEvent,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    events = payload if isinstance(payload, list) else [payload]
    for ev in events:
        assert_context_matches(context, ev.tenant_id, ev.env)
    svc = get_budget_service()
    return {"items": svc.record_usage(context, events)}


@router.get("")
def list_usage(
    surface: Optional[str] = None,
    provider: Optional[str] = None,
    model_or_plan_id: Optional[str] = None,
    tool_type: Optional[str] = None,
    window_days: int = Query(7, ge=1, le=90),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    svc = get_budget_service()
    items = svc.query_usage(
        context,
        surface=surface,
        provider=provider,
        model_or_plan_id=model_or_plan_id,
        tool_type=tool_type,
        window_days=window_days,
        limit=limit,
        offset=offset,
    )
    return {"items": items}


@router.get("/summary")
def usage_summary(
    surface: Optional[str] = None,
    window_days: int = Query(7, ge=1, le=90),
    group_by: Optional[str] = Query("provider"),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    svc = get_budget_service()
    return svc.summary(context, window_days=window_days, surface=surface, group_by=group_by)
