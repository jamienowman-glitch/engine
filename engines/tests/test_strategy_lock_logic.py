
import unittest
import sys
from unittest.mock import MagicMock, patch

# Aggressive Mocking
mock_fastapi = MagicMock()
mock_pydantic = MagicMock()
sys.modules["fastapi"] = mock_fastapi
sys.modules["pydantic"] = mock_pydantic

# Mock models
class StubStrategyDecision:
    def __init__(self, allowed, reason=None, lock_id=None, three_wise_verdict=None):
        self.allowed = allowed
        self.reason = reason
        self.lock_id = lock_id
        self.three_wise_verdict = three_wise_verdict

class StubStrategyLockConfig:
    def __init__(self, defaults=None, overrides=None):
        self.defaults = defaults or {}
        self.overrides = overrides or {}

# Mock imports in sys.modules so test file can run
# Mock models module
mock_res_mod = MagicMock()
sys.modules["engines.strategy_lock.models"] = mock_res_mod
mock_res_mod.StrategyDecision = StubStrategyDecision

# Mock config repository module fully to avoid pydantic issues in real file
mock_config_repo_mod = MagicMock()
sys.modules["engines.strategy_lock.config_repository"] = mock_config_repo_mod
mock_config_repo_mod.StrategyLockConfig = StubStrategyLockConfig
# We need to expose get_strategy_lock_config_repo that the resolution logic calls
# We'll mock that inside the test via patch, or set it on the mock module
# resolution.py does: `from engines.strategy_lock.config_repository import get_strategy_lock_config_repo`

from engines.common.identity import RequestContext
# Import resolution now that dependencies are mocked
from engines.strategy_lock.resolution import resolve_strategy_lock

class TestStrategyLock(unittest.TestCase):
    def setUp(self):
        self.ctx = RequestContext(
            tenant_id="t_system", mode="saas", project_id="p1", request_id="r1", 
            trace_id="tr1", run_id="run1", step_id="step1", user_id="u1", surface_id="s1"
        )
        # Setup config repo mock
        self.mock_config_repo = MagicMock()
        mock_config_repo_mod.get_strategy_lock_config_repo.return_value = self.mock_config_repo
        # Default config
        self.mock_config_repo.get.return_value = StubStrategyLockConfig()

    @patch("engines.strategy_lock.resolution.get_strategy_lock_service")
    def test_resolution_default_open(self, mock_get_service):
        # Default: no config, so required=False
        decision = resolve_strategy_lock(self.ctx, action="tool_x")
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, "strategy_lock_not_required")

    @patch("engines.strategy_lock.resolution.get_strategy_lock_service")
    def test_resolution_required_blocked(self, mock_get_service):
        # Configure tool requirement
        self.mock_config_repo.get.return_value = StubStrategyLockConfig(defaults={"require_for_tools": True})
        
        # Mock service to say "Not allowed" (no active lock)
        mock_service = MagicMock()
        mock_service.check_action_allowed.return_value = StubStrategyDecision(allowed=False, reason="no_lock")
        mock_get_service.return_value = mock_service
        
        decision = resolve_strategy_lock(self.ctx, action="tool_x")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "no_lock") # Or enhanced reason

    @patch("engines.strategy_lock.resolution.get_strategy_lock_service")
    def test_resolution_required_allowed(self, mock_get_service):
        self.mock_config_repo.get.return_value = StubStrategyLockConfig(defaults={"require_for_tools": True})
        
        mock_service = MagicMock()
        mock_service.check_action_allowed.return_value = StubStrategyDecision(allowed=True, lock_id="lock-1")
        mock_get_service.return_value = mock_service
        
        decision = resolve_strategy_lock(self.ctx, action="tool_x")
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.lock_id, "lock-1")

    @patch("engines.strategy_lock.resolution.get_strategy_lock_service")
    def test_scope_override_node(self, mock_get_service):
        # Default: tools required. Override: Node-A NOT required.
        config = StubStrategyLockConfig(
            defaults={"require_for_tools": True},
            overrides={"nodes": {"node_a": False}}
        )
        self.mock_config_repo.get.return_value = config
        
        # Action on node_a
        decision = resolve_strategy_lock(self.ctx, action="tool_x", subject_type="node", subject_id="node_a")
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, "strategy_lock_not_required")
        
        # Action on node_b (fallback to default required)
        mock_service = MagicMock()
        mock_service.check_action_allowed.return_value = StubStrategyDecision(allowed=False)
        mock_get_service.return_value = mock_service
        
        decision_b = resolve_strategy_lock(self.ctx, action="tool_x", subject_type="node", subject_id="node_b")
        self.assertFalse(decision_b.allowed)

if __name__ == "__main__":
    unittest.main()
