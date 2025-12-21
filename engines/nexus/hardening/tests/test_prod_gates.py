"""Tests for Phase 9 Production Gates."""
import time
from unittest import mock
import pytest
import os
from fastapi import FastAPI, Depends, HTTPException

from engines.common.identity import RequestContext, get_request_context
from engines.kill_switch.models import KillSwitch, KillSwitchUpdate
from engines.kill_switch.service import KillSwitchService
from engines.kill_switch.repository import InMemoryKillSwitchRepository
from engines.nexus.hardening.rate_limit import RateLimitService

# Mock Dependencies
def mock_get_context():
    # Helper to return a context; normally injected by test client overrides
    pass

# We will test the logical components mostly, as full integration requires wiring the app
# But we can test the behavior of the controls isolated and then simulates logic.

def test_kill_switch_blocking():
    repo = InMemoryKillSwitchRepository()
    service = KillSwitchService(repo=repo)
    
    ctx = RequestContext(tenant_id="t_blocked", env="prod", user_id="u1")
    
    # 1. By default allowed
    service.ensure_action_allowed(ctx, "nexus_read")
    
    # 2. Block 'nexus_read'
    service.upsert(ctx, KillSwitchUpdate(disabled_actions=["nexus_read"]))
    
    with pytest.raises(HTTPException) as exc:
        service.ensure_action_allowed(ctx, "nexus_read")
    assert exc.value.status_code == 403
    
    # 3. Other actions allowed
    service.ensure_action_allowed(ctx, "other_action")


def test_rate_limiter():
    limiter = RateLimitService()
    ctx = RequestContext(tenant_id="t_spam", env="dev", user_id="u1")
    
    # Limit to 5 per 1 sec
    limit = 5
    window = 1.0
    
    for _ in range(5):
        limiter.check_rate_limit(ctx, action="test_action", limit=limit, window=window)
        
    # 6th should fail
    with pytest.raises(HTTPException) as exc:
        limiter.check_rate_limit(ctx, action="test_action", limit=limit, window=window)
    assert exc.value.status_code == 429

    
def test_tenancy_isolation_in_limits():
    """Verify rate limits don't leak across tenants."""
    limiter = RateLimitService()
    ctx1 = RequestContext(tenant_id="t_1", env="dev", user_id="u1")
    ctx2 = RequestContext(tenant_id="t_2", env="dev", user_id="u2")
    
    limit = 1
    
    # T1 uses quota
    limiter.check_rate_limit(ctx1, "act", limit=1, window=10)
    
    # T2 should still work
    limiter.check_rate_limit(ctx2, "act", limit=1, window=10)
    
    with pytest.raises(HTTPException):
        limiter.check_rate_limit(ctx1, "act", limit=1, window=10)


def test_gate_chain_allows_missing_when_flagged():
    from engines.nexus.hardening.gate_chain import GateChain
    
    # 1. Default (strict) behavior: Ensure flag is OFF even if passed in env
    with mock.patch.dict(os.environ, {"GATECHAIN_ALLOW_MISSING": ""}):
        gc = GateChain()
        ctx = RequestContext(tenant_id="t_1", env="prod", user_id="u1")
        
        # Missing budget -> 403
        with pytest.raises(HTTPException) as exc:
            # Mocking budget service summary to work but resolver returns None by default for unknown surface
            with mock.patch("engines.budget.service.BudgetService.summary"):
                gc._enforce_budget(ctx, "unknown_surface", "act")
        assert exc.value.status_code == 403
    
    # 2. With flag
    with mock.patch.dict(os.environ, {"GATECHAIN_ALLOW_MISSING": "1"}):
        with mock.patch("engines.budget.service.BudgetService.summary"):
             # Should not raise
            gc._enforce_budget(ctx, "unknown_surface", "act")
