from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from engines.common.identity import RequestContext, assert_context_matches, get_request_context
from engines.common.error_envelope import error_response
from engines.identity.auth import get_auth_context, require_tenant_membership, require_tenant_role
from engines.strategy_lock.models import StrategyLock, StrategyLockCreate, StrategyLockUpdate, StrategyStatus
from engines.strategy_lock.repository import StrategyLockRepository
from engines.strategy_lock.service import StrategyLockService, get_strategy_lock_service
from engines.strategy_lock.config_repository import get_strategy_lock_config_repo, StrategyLockConfig
from engines.strategy_lock.policy import (
    StrategyPolicyBinding,
    StrategyPolicyService,
    get_strategy_policy_service,
)
from engines.strategy_lock.resolution import resolve_strategy_lock
from engines.logging.audit import emit_audit_event

router = APIRouter(prefix="/strategy-locks", tags=["strategy_lock"])
policy_router = APIRouter(prefix="/strategy-lock", tags=["strategy_lock"])


class StrategyPolicyPayload(BaseModel):
    bindings: List[StrategyPolicyBinding]


def _require_policy_membership(context: RequestContext, auth) -> None:
    try:
        require_tenant_membership(auth, context.tenant_id)
    except HTTPException as exc:
        error_response(
            code="auth.tenant_membership_required",
            message=str(exc.detail),
            status_code=exc.status_code,
            resource_kind="strategy_policy_store",
        )


@policy_router.get("/policy", response_model=list[StrategyPolicyBinding])
def get_strategy_policy(
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
    service: StrategyPolicyService = Depends(get_strategy_policy_service),
) -> list[StrategyPolicyBinding]:
    _require_policy_membership(context, auth)
    try:
        return service.list_policies(context)
    except HTTPException:
        raise
    except Exception as exc:
        error_response(
            code="strategy_policy.policy_read_failed",
            message=str(exc),
            status_code=500,
            resource_kind="strategy_policy_store",
        )


@policy_router.put("/policy", response_model=list[StrategyPolicyBinding])
def put_strategy_policy(
    payload: StrategyPolicyPayload,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
    service: StrategyPolicyService = Depends(get_strategy_policy_service),
) -> list[StrategyPolicyBinding]:
    _require_policy_membership(context, auth)
    try:
        return service.save_policies(context, payload.bindings)
    except HTTPException:
        raise
    except Exception as exc:
        error_response(
            code="strategy_policy.policy_write_failed",
            message=str(exc),
            status_code=500,
            resource_kind="strategy_policy_store",
        )


@router.post("", response_model=StrategyLock)
def create_strategy_lock(
    payload: StrategyLockCreate,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    try:
        require_tenant_membership(auth, context.tenant_id)
    except HTTPException as exc:
        error_response(
            code="auth.tenant_membership_required",
            message=str(exc.detail),
            status_code=exc.status_code,
            resource_kind="strategy_lock",
        )
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
    try:
        require_tenant_membership(auth, context.tenant_id)
    except HTTPException as exc:
        error_response(
            code="auth.tenant_membership_required",
            message=str(exc.detail),
            status_code=exc.status_code,
            resource_kind="strategy_lock",
        )
    return get_strategy_lock_service().list_locks(context, status=status, surface=surface, scope=scope)


@router.get("/{lock_id}", response_model=StrategyLock)
def get_strategy_lock(
    lock_id: str,
    version: int | None = Query(None),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    try:
        require_tenant_membership(auth, context.tenant_id)
    except HTTPException as exc:
        error_response(
            code="auth.tenant_membership_required",
            message=str(exc.detail),
            status_code=exc.status_code,
            resource_kind="strategy_lock",
        )
    return get_strategy_lock_service().get_lock(context, lock_id, version=version)


@router.patch("/{lock_id}", response_model=StrategyLock)
def update_strategy_lock(
    lock_id: str,
    payload: StrategyLockUpdate,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    try:
        require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    except HTTPException as exc:
        error_response(
            code="auth.insufficient_role",
            message=str(exc.detail),
            status_code=exc.status_code,
            resource_kind="strategy_lock",
        )
    return get_strategy_lock_service().update_lock(context, lock_id, payload)


@router.post("/prepare")
async def prepare_strategy_lock(
    payload: dict, # TODO: schema
    context: RequestContext = Depends(get_request_context),
) -> dict:
    """
    Prepare a strategy lock for a specific scope/intent (Chat invocation).
    Does NOT execute.
    """
    # 1. Calculate required scope from payload
    # 2. Check if lock already exists
    # 3. If not, create PENDING lock
    # 4. Return lock info
    
    # For MVP, just creating a pending lock via existing service logic
    # But we need to translate "intent" to LockCreate
    service = get_strategy_lock_service(context)
    
    # Using generic dict payload for now to match prompt "Chat-Compatible Invocation"
    # Scope: {surface_id, graph_id...}
    scope_data = payload.get("scope", {})
    intent = payload.get("intent_summary", "Manual Lock Request")
    actions = payload.get("action_names", ["*"]) # default to all if not specified? Or explicit.
    
    # Map scope to lock.scope string? "surface:X" or "node:Y"?
    # For now, let's say scope="surface:{surface_id}" or just generic
    scope_str = "global"
    if scope_data.get("node_id"):
        scope_str = f"node:{scope_data['node_id']}"
    elif scope_data.get("graph_id"):
        scope_str = f"graph:{scope_data['graph_id']}"
    elif scope_data.get("surface_id"):
        scope_str = f"surface:{scope_data['surface_id']}"
        
    lock_create = StrategyLockCreate(
        surface=scope_data.get("surface_id"),
        scope=scope_str,
        title=f"Lock for {intent}",
        description=intent,
        allowed_actions=actions,
        # Default constraints?
    )
    
    lock = service.create_lock(context, lock_create)
    return {"status": "prepared", "lock": lock}


@router.get("/config/strategy-lock")
async def get_strategy_lock_config(
    context: RequestContext = Depends(get_request_context),
) -> StrategyLockConfig:
    repo = get_strategy_lock_config_repo()
    return repo.get(context)


@router.put("/config/strategy-lock")
async def update_strategy_lock_config(
    config: StrategyLockConfig,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
) -> StrategyLockConfig:
    repo = get_strategy_lock_config_repo()
    try:
        require_tenant_membership(auth, context.tenant_id)
        require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    except HTTPException as exc:
        error_response(
            code="auth.insufficient_role",
            message=str(exc.detail),
            status_code=exc.status_code,
            resource_kind="strategy_lock",
        )
    return repo.update(context, config)


@router.post("/{lock_id}/approve", response_model=StrategyLock)
def approve_strategy_lock(
    lock_id: str,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    try:
        require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    except HTTPException as exc:
        error_response(
            code="auth.insufficient_role",
            message=str(exc.detail),
            status_code=exc.status_code,
            resource_kind="strategy_lock",
        )
    return get_strategy_lock_service().approve_lock(context, lock_id)


@router.post("/{lock_id}/reject", response_model=StrategyLock)
def reject_strategy_lock(
    lock_id: str,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    try:
        require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    except HTTPException as exc:
        error_response(
            code="auth.insufficient_role",
            message=str(exc.detail),
            status_code=exc.status_code,
            resource_kind="strategy_lock",
        )
    return get_strategy_lock_service().reject_lock(context, lock_id)
