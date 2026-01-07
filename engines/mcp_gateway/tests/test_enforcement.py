import pytest
from unittest.mock import MagicMock, patch
from engines.common.identity import RequestContext
from engines.mcp_gateway import server
from engines.mcp_gateway.inventory import Tool, Scope, get_inventory
from fastapi.testclient import TestClient

# Mock Inventory
@pytest.fixture
def mock_inventory():
    inv = get_inventory()
    # Reset
    inv._tools = {}
    from pydantic import BaseModel
    class Empty(BaseModel): pass
    
    async def dummy_handler(ctx, args): return "ok"
    
    # Register Dummy Tool
    tool = Tool(id="dummy", name="Dummy", summary="Test")
    tool.register_scope(Scope("safe", "Safe Scope", Empty, dummy_handler))
    tool.register_scope(Scope("dangerous", "Dangerous Scope", Empty, dummy_handler))
    inv.register_tool(tool)
    return inv

def test_gatechain_called_success(mock_inventory):
    # Mock GateChain
    with patch("engines.nexus.hardening.gate_chain.get_gate_chain") as mock_get_chain:
        mock_chain = MagicMock()
        mock_get_chain.return_value = mock_chain
        
        client = TestClient(server.app)
        
        payload = {
            "tool_id": "dummy",
            "scope_name": "safe",
            "arguments": {}
        }
        headers = {
            "X-Tenant-Id": "t_test",
            "X-Mode": "lab",
            "X-Project-Id": "p_test",
            "X-Surface-Id": "s_test",
            "X-App-Id": "a_test",
            "X-User-Id": "u_test"
        }
        
        resp = client.post("/tools/call", json=payload, headers=headers)
        
        if resp.status_code != 200:
             print(f"Debug Resp: {resp.json()}")
        
        assert resp.status_code == 200
        assert resp.json()["result"] == "ok" # Changed to match server return {"result": ...}
        
        # Verify GateChain called
        mock_chain.run.assert_called_once()
        _, kwargs = mock_chain.run.call_args
        assert kwargs["action"] == "dummy.safe"

def test_gatechain_blocks(mock_inventory):
    # Mock GateChain to raise exception
    with patch("engines.nexus.hardening.gate_chain.get_gate_chain") as mock_get_chain:
        mock_chain = MagicMock()
        mock_get_chain.return_value = mock_chain
        
        from engines.common.error_envelope import error_response
        from fastapi import HTTPException
        
        def mock_run(*args, **kwargs):
             # Simulate Block
             # Simulating what error_response does: raises HTTPException with detail dict
             raise HTTPException(status_code=403, detail={"error": {"code": "firearms.license_required"}})
        
        mock_chain.run.side_effect = mock_run

        client = TestClient(server.app)
        
        payload = {
            "tool_id": "dummy",
            "scope_name": "dangerous",
            "arguments": {}
        }
        headers = {
            "X-Tenant-Id": "t_test",
            "X-Mode": "lab",
            "X-Project-Id": "p_test",
            "X-Surface-Id": "s_test",
            "X-App-Id": "a_test",
            "X-User-Id": "u_test"
        }
        
        resp = client.post("/tools/call", json=payload, headers=headers)
        
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "firearms.license_required"
        mock_chain.run.assert_called_once()
