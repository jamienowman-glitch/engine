
import unittest
import sys
from unittest.mock import MagicMock, patch

# Aggressive Mocking
mock_fastapi = MagicMock()
mock_pydantic = MagicMock()
sys.modules["fastapi"] = mock_fastapi
sys.modules["pydantic"] = mock_pydantic

# Mock models
class StubFirearmBinding:
    def __init__(self, action_name, firearm_id, strategy_lock_required=True):
        self.action_name = action_name
        self.firearm_id = firearm_id
        self.strategy_lock_required = strategy_lock_required

class StubFirearmGrant:
    def __init__(self, firearm_id, granted_to_agent_id=None, tenant_id=None, expires_at=None, revoked=False):
        self.firearm_id = firearm_id
        self.granted_to_agent_id = granted_to_agent_id
        self.tenant_id = tenant_id
        self.expires_at = expires_at
        self.revoked = revoked

class StubFirearmDecision:
    def __init__(self, allowed, reason=None, firearm_id=None, required_license_types=None, strategy_lock_required=False):
        self.allowed = allowed
        self.reason = reason
        self.firearm_id = firearm_id
        self.required_license_types = required_license_types or []
        self.strategy_lock_required = strategy_lock_required

mock_models = MagicMock()
sys.modules["engines.firearms.models"] = mock_models
mock_models.FirearmBinding = StubFirearmBinding
mock_models.FirearmGrant = StubFirearmGrant
mock_models.FirearmDecision = StubFirearmDecision

from engines.common.identity import RequestContext
from engines.firearms.service import FirearmsService

class TestFirearmsLogic(unittest.TestCase):
    def setUp(self):
        self.ctx = RequestContext(
            tenant_id="t_sys", mode="saas", project_id="p1", request_id="r1", 
            trace_id="tr1", run_id="run1", step_id="step1", user_id="u1", surface_id="s1",
            actor_id="agent_1"
        )
        self.ctx.actor_type = "agent"
        self.mock_repo = MagicMock()
        self.service = FirearmsService(repo=self.mock_repo)

    def test_no_binding_allowed(self):
        self.mock_repo.get_binding.return_value = None
        decision = self.service.check_access(self.ctx, "tool.safe_action")
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, "no_binding")

    def test_binding_no_grant_blocked(self):
        binding = StubFirearmBinding("tool.dangerous", "firearm.db")
        self.mock_repo.get_binding.return_value = binding
        self.mock_repo.list_grants.return_value = [] # No grants
        
        decision = self.service.check_access(self.ctx, "tool.dangerous")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "firearms.license_required")
        self.assertEqual(decision.firearm_id, "firearm.db")
        self.assertIn("firearm.db", decision.required_license_types)

    def test_binding_valid_grant_allowed(self):
        binding = StubFirearmBinding("tool.dangerous", "firearm.db")
        grant = StubFirearmGrant("firearm.db", granted_to_agent_id="agent_1", tenant_id="t_sys")
        
        self.mock_repo.get_binding.return_value = binding
        self.mock_repo.list_grants.return_value = [grant]
        
        decision = self.service.check_access(self.ctx, "tool.dangerous")
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, "grant_valid")
        self.assertTrue(decision.strategy_lock_required)

if __name__ == "__main__":
    unittest.main()
