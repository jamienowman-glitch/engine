from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from engines.common.identity import RequestContext, assert_context_matches, get_request_context
from engines.identity.auth import get_auth_context, require_tenant_membership, require_tenant_role
from engines.strategy_lock.models import StrategyLock, StrategyLockCreate, StrategyLockUpdate, StrategyStatus
from engines.strategy_lock.service import get_strategy_lock_service

router = APIRouter(prefix="/strategy-locks", tags=["strategy_lock"])


@router.post("", response_model=StrategyLock)
def create_strategy_lock(
    payload: StrategyLockCreate,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    svc = get_strategy_lock_service()
    return svc.create_lock(context, payload)


@router.get("", response_model=list[StrategyLock])
def list_strategy_locks(
    status: Optional[StrategyStatus] = None,
    surface: Optional[str] = None,
    scope: Optional[str] = None,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    return get_strategy_lock_service().list_locks(context, status=status, surface=surface, scope=scope)


@router.get("/{lock_id}", response_model=StrategyLock)
def get_strategy_lock(
    lock_id: str,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    return get_strategy_lock_service().get_lock(context, lock_id)


@router.patch("/{lock_id}", response_model=StrategyLock)
def update_strategy_lock(
    lock_id: str,
    payload: StrategyLockUpdate,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    return get_strategy_lock_service().update_lock(context, lock_id, payload)


@router.post("/{lock_id}/approve", response_model=StrategyLock)
def approve_strategy_lock(
    lock_id: str,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    return get_strategy_lock_service().approve_lock(context, lock_id)


@router.post("/{lock_id}/reject", response_model=StrategyLock)
def reject_strategy_lock(
    lock_id: str,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    return get_strategy_lock_service().reject_lock(context, lock_id)
