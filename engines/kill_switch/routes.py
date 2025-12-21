from __future__ import annotations

from fastapi import APIRouter, Depends

from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import get_auth_context, require_tenant_membership, require_tenant_role
from engines.kill_switch.models import KillSwitch, KillSwitchUpdate
from engines.kill_switch.service import get_kill_switch_service
from engines.strategy_lock.service import get_strategy_lock_service
from engines.strategy_lock.models import ACTION_KILL_SWITCH_UPDATE

router = APIRouter(prefix="/kill-switches", tags=["kill_switches"])


@router.get("", response_model=KillSwitch | None)
def get_switch(
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    return get_kill_switch_service().get(context)


@router.put("", response_model=KillSwitch)
def upsert_switch(
    payload: KillSwitchUpdate,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    get_strategy_lock_service().require_strategy_lock_or_raise(context, surface=None, action=ACTION_KILL_SWITCH_UPDATE)
    return get_kill_switch_service().upsert(context, payload)
