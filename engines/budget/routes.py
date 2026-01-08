from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from engines.budget.models import BudgetPolicy, UsageEvent
from engines.budget.repository import get_budget_policy_repo
from engines.budget.service import BudgetService, get_budget_service
from engines.common.identity import RequestContext, assert_context_matches, get_request_context
from engines.common.error_envelope import error_response
from engines.identity.auth import get_auth_context, require_tenant_membership

router = APIRouter(prefix="/budget", tags=["budget"])


def _ensure_membership(auth, context: RequestContext) -> None:
    """Wrap tenant membership errors in uniform envelope."""
    try:
        require_tenant_membership(auth, context.tenant_id)
    except HTTPException as exc:
        error_response(
            code="auth.tenant_membership_required",
            message=str(exc.detail),
            status_code=exc.status_code,
            resource_kind="budget",
        )


@router.post("/usage")
def post_usage(
    payload: List[UsageEvent] | UsageEvent,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    _ensure_membership(auth, context)
    events = payload if isinstance(payload, list) else [payload]
    for ev in events:
        assert_context_matches(context, ev.tenant_id, ev.env)
    svc = get_budget_service()
    return {"items": svc.record_usage(context, events)}


@router.get("/usage")
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
    _ensure_membership(auth, context)
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


@router.get("/usage/summary")
def usage_summary(
    surface: Optional[str] = None,
    window_days: int = Query(7, ge=1, le=90),
    group_by: Optional[str] = Query("provider"),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    _ensure_membership(auth, context)
    svc = get_budget_service()
    return svc.summary(context, window_days=window_days, surface=surface, group_by=group_by)


class BudgetPolicyPayload(BaseModel):
    surface: Optional[str] = None
    mode: Optional[str] = None
    app: Optional[str] = None
    threshold: Decimal


@router.put("/policy")
def upsert_policy(
    payload: BudgetPolicyPayload,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    _ensure_membership(auth, context)
    repo = get_budget_policy_repo()
    policy = BudgetPolicy(
        tenant_id=context.tenant_id,
        env=context.env,
        surface=payload.surface or context.surface_id,
        mode=payload.mode or context.mode,
        app=payload.app or context.app_id,
        threshold=payload.threshold,
    )
    saved = repo.save_policy(policy)
    return saved.model_dump()


@router.get("/policy")
def read_policy(
    surface: Optional[str] = Query(None),
    mode: Optional[str] = Query(None),
    app: Optional[str] = Query(None),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    _ensure_membership(auth, context)
    repo = get_budget_policy_repo()
    policy = repo.get_policy(
        tenant_id=context.tenant_id,
        env=context.env,
        surface=surface or context.surface_id,
        mode=mode or context.mode,
        app=app or context.app_id,
    )
    if not policy:
        error_response(
            code="budget.policy_not_found",
            message="Budget policy not found",
            status_code=404,
            resource_kind="budget_policy",
            details={
                "surface": surface or context.surface_id,
                "mode": mode or context.mode,
                "app": app or context.app_id,
            },
        )
    return policy.model_dump()
