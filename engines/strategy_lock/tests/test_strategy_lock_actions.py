from __future__ import annotations

import os

from engines.common.identity import RequestContext
from engines.strategy_lock.models import (
    ACTION_BUILDER_PUBLISH_PAGE,
    ACTION_SEO_PAGE_CONFIG_UPDATE,
    StrategyLock,
    StrategyStatus,
)
from engines.strategy_lock.repository import InMemoryStrategyLockRepository
from engines.strategy_lock.service import StrategyLockService


def test_builder_actions_require_lock():
    repo = InMemoryStrategyLockRepository()
    svc = StrategyLockService(repo=repo)
    ctx = RequestContext(tenant_id="t_demo", env="dev", user_id="u1")
    decision = svc.check_action_allowed(ctx, surface="squared", action=ACTION_BUILDER_PUBLISH_PAGE)
    assert not decision.allowed
    # add approved lock
    lock = StrategyLock(
        tenant_id=ctx.tenant_id,
        env=ctx.env,
        surface="squared",
        scope="app_toggle",
        title="Allow publish",
        constraints={},
        allowed_actions=[ACTION_BUILDER_PUBLISH_PAGE, ACTION_SEO_PAGE_CONFIG_UPDATE],
        created_by_user_id=ctx.user_id,
        status=StrategyStatus.approved,
    )
    repo.create(ctx, lock)
    decision2 = svc.check_action_allowed(ctx, surface="squared", action=ACTION_BUILDER_PUBLISH_PAGE)
    assert decision2.allowed
