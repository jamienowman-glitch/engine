from __future__ import annotations

from typing import Optional

from engines.common.identity import RequestContext
from engines.strategy_lock.config_repository import get_strategy_lock_config_repo
from engines.strategy_lock.models import StrategyDecision
from engines.strategy_lock.policy import get_strategy_policy_service
from engines.strategy_lock.service import get_strategy_lock_service


def resolve_strategy_lock(
    ctx: RequestContext,
    surface: Optional[str] = None,
    action: Optional[str] = None,
    subject_type: Optional[str] = None,
    subject_id: Optional[str] = None,
) -> StrategyDecision:
    """
    Resolve whether strategy lock is required and satisfied for the given context.
    """
    config = get_strategy_lock_config_repo().get(ctx)
    policy_service = get_strategy_policy_service()
    action_name = action or ""
    target_surface = surface or ctx.surface_id

    if config.defaults.get("enabled") is False:
        return StrategyDecision(allowed=True, reason="strategy_lock_disabled", lock_id=None, three_wise_verdict=None)

    if not policy_service.requires_strategy_lock(ctx, action_name, target_surface):
        return StrategyDecision(allowed=True, reason="strategy_lock_not_required", lock_id=None, three_wise_verdict=None)

    service = get_strategy_lock_service()
    decision = service.check_action_allowed(ctx, surface, action or "*")
    if not decision.allowed:
        decision.reason = decision.reason or "strategy_lock.approval_required"
    return decision
