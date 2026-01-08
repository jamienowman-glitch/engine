import pytest
from unittest.mock import MagicMock
from decimal import Decimal
from fastapi import HTTPException
from engines.nexus.hardening.gate_chain import GateChain
from engines.common.identity import RequestContext

def test_gate_chain_enforces_daily_cap():
    # 1. Setup Mock Budget Service
    mock_budget = MagicMock()
    # Scenario: Tool has spent $4.00 already
    mock_budget.get_tool_spend.return_value = Decimal("4.00")
    
    # 2. Setup GateChain
    # Mock other services to avoid noise
    chain = GateChain(
        kill_switch_service=MagicMock(),
        firearms_service=MagicMock(),
        strategy_lock_service=MagicMock(),
        budget_service=mock_budget,
        kpi_service=MagicMock(),
        temperature_service=MagicMock(),
        budget_policy_repo=MagicMock(),
        audit_logger=MagicMock()
    )
    
    # Mock allow checks on other services
    chain.kill_switch.ensure_action_allowed.return_value = None
    chain.firearms.check_access.return_value = MagicMock(allowed=True)
    chain.strategy_lock.resolve.return_value = MagicMock(allowed=True) # Assuming resolve usage if updated, but let's check what run() calls.
    # Actually run() calls resolve_strategy_lock imported from module, which we can't easily mock here without patching.
    # BUT, if we use `with patch` it works.
    # OR we rely on the fact that `run` calls `self.strategy_lock` methods?
    # Wait, previous `run` implementation used `resolve_strategy_lock` global function.
    # Let's mock `resolve_strategy_lock` via patch.

    ctx = RequestContext(tenant_id="t_test", env="dev", mode="lab", user_id="u1")
    
    from unittest.mock import patch
    with patch("engines.nexus.hardening.gate_chain.resolve_strategy_lock") as mock_resolve:
        mock_resolve.return_value.allowed = True
        
        # 3. Test Pass Case (Cost $0.50 + Spend $4.00 <= Cap $5.00)
        chain.run(
            ctx, 
            action="tool.test", 
            surface="nexus", 
            subject_type="tool", 
            subject_id="tool-a",
            skip_metrics=True,
            budget_check={"cost": 0.50, "daily_cap": 5.00, "tool_id": "tool-a"}
        )
        
        # 4. Test Block Case (Cost $2.00 + Spend $4.00 > Cap $5.00)
        with pytest.raises(HTTPException) as exc:
            chain.run(
                ctx, 
                action="tool.test", 
                surface="nexus", 
                subject_type="tool", 
                subject_id="tool-a",
                skip_metrics=True,
                budget_check={"cost": 2.00, "daily_cap": 5.00, "tool_id": "tool-a"}
            )
        assert exc.value.status_code == 403
        assert "Daily budget cap exceeded" in str(exc.value.detail)
