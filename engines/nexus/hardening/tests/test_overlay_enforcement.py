"""Integration tests for Overlay Enforcement in GateChain."""
from __future__ import annotations

import pytest
from fastapi import HTTPException
from types import SimpleNamespace
from typing import Optional

from engines.common.identity import RequestContext
from engines.firearms.models import FirearmBinding, FirearmDecision, FirearmGrant
from engines.firearms.repository import InMemoryFirearmsRepository
from engines.firearms.service import FirearmsService
from engines.nexus.hardening.gate_chain import GateChain

# Minimal stubs for non-firearms services
class _StubService:
    def summary(self, *args, **kwargs): return {"total_cost": 0}
    def list_corridors(self, *args, **kwargs): 
        # Return a corridor with no floor/ceiling to satisfy strict check but allow everything
        return [SimpleNamespace(kpi_name="any_kpi", floor=None, ceiling=None)]
    def latest_raw_measurement(self, *args, **kwargs): return None
    def compute_temperature(self, *args, **kwargs): return SimpleNamespace(floors_breached=[], ceilings_breached=[])
    def upsert(self, *args, **kwargs): pass
    def ensure_action_allowed(self, *args, **kwargs): pass
    def require_strategy_lock_or_raise(self, *args, **kwargs): pass

class _StubBudgetRepo:
    def get_policy(self, *args, **kwargs):
        # Return a permissive policy
        return SimpleNamespace(
            surface="nexus",
            mode="lab",
            app="any",
            threshold=1000000
        )

# Mock resolve_strategy_lock to always allow
def _mock_resolve_strategy_lock(*args, **kwargs):
    return SimpleNamespace(allowed=True, three_wise_verdict=None, lock_id=None)

@pytest.fixture
def gate_chain_setup(monkeypatch):
    """Setup GateChain with a real FirearmsService backed by InMemory repository."""
    
    # 1. Setup Firearms
    repo = InMemoryFirearmsRepository()
    firearms_service = FirearmsService(repo=repo)
    
    # 2. Setup GateChain with stubbed neighbours
    gate_chain = GateChain(
        kill_switch_service=_StubService(),
        firearms_service=firearms_service,
        strategy_lock_service=_StubService(),
        budget_service=_StubService(),
        kpi_service=_StubService(),
        temperature_service=_StubService(),
        budget_policy_repo=_StubBudgetRepo(),
        audit_logger=lambda *args, **kwargs: None
    )
    
    # Monkeypatch strategy resolution to avoid external deps
    monkeypatch.setattr("engines.nexus.hardening.gate_chain.resolve_strategy_lock", _mock_resolve_strategy_lock)
    
    return gate_chain, repo

def test_gate_chain_default_safe_unbound_tool(gate_chain_setup):
    """Test that a tool with no overlay binding is allowed by default."""
    gate_chain, _ = gate_chain_setup
    ctx = RequestContext(
        tenant_id="t_test", 
        env="dev", 
        mode="lab", 
        surface_id="nexus",
        request_id="req-1"
    )
    
    # Action has no binding
    action = "tool.safe_tool.method"
    
    # Should not raise
    try:
        gate_chain.run(ctx, action=action, surface="nexus", subject_type="tool", subject_id="safe_tool")
    except HTTPException:
        pytest.fail("GateChain raised HTTPException for unbound (safe) tool")

def test_gate_chain_enforces_binding_without_grant(gate_chain_setup):
    """Test that a bound tool blocks execution if no grant exists."""
    gate_chain, repo = gate_chain_setup
    ctx = RequestContext(
        tenant_id="t_test", 
        env="dev", 
        mode="lab", 
        surface_id="nexus",
        user_id="u1",
        request_id="req-2"
    )
    
    # 1. Bind action to a firearm
    action = "tool.dangerous.nuke"
    firearm_id = "firearm.nuke_license"
    repo.create_binding(ctx, FirearmBinding(
        action_name=action,
        firearm_id=firearm_id
    ))
    
    # 2. Run without grant - EXPECT BLOCK
    with pytest.raises(HTTPException) as exc:
        gate_chain.run(ctx, action=action, surface="nexus", subject_type="tool", subject_id="dangerous")
    
    assert exc.value.status_code == 403
    error = exc.value.detail["error"]
    assert error["code"] == "firearms.license_required"
    assert "firearm.nuke_license" in error["details"]["required_license_types"]

def test_gate_chain_allows_binding_with_grant(gate_chain_setup):
    """Test that a bound tool is allowed if the user has the grant."""
    gate_chain, repo = gate_chain_setup
    ctx = RequestContext(
        tenant_id="t_test", 
        env="dev", 
        mode="lab", 
        surface_id="nexus",
        user_id="u1",
        request_id="req-3"
    )
    
    # 1. Bind action
    action = "tool.sensitive.read"
    firearm_id = "firearm.read_pii"
    repo.create_binding(ctx, FirearmBinding(
        action_name=action,
        firearm_id=firearm_id
    ))
    
    # 2. Grant license to user
    repo.create_grant(ctx, FirearmGrant(
        firearm_id=firearm_id,
        granted_to_user_id="u1",
        tenant_id="t_test"
    ))
    
    # 3. Run - EXPECT PASS
    try:
        gate_chain.run(ctx, action=action, surface="nexus", subject_type="tool", subject_id="sensitive")
    except HTTPException as e:
        pytest.fail(f"GateChain blocked authorized user: {e.detail}")
