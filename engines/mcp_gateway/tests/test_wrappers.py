import sys
from unittest.mock import MagicMock

# --- Mock Feature Flags to bypass Firestore requirement ---
mock_ff_repo = MagicMock()
mock_ff_repo.feature_flag_repo = MagicMock()
sys.modules["engines.feature_flags"] = MagicMock()
sys.modules["engines.feature_flags.repository"] = mock_ff_repo
sys.modules["engines.feature_flags.service"] = MagicMock()
mock_routes = MagicMock()
mock_routes.router = MagicMock()
sys.modules["engines.feature_flags.routes"] = mock_routes

from fastapi.testclient import TestClient
from engines.mcp_gateway import server

def test_inventory_completeness():
    client = TestClient(server.app)
    headers = {
        "X-Tenant-Id": "t_demo",
        "X-Mode": "lab",
        "X-Project-Id": "p_test",
        "X-Surface-Id": "s_test",
        "X-App-Id": "a_test"
    }
    
    resp = client.post("/tools/list", json={}, headers=headers)
    if resp.status_code != 200:
        print(f"Debug Resp: {resp.json()}")
    assert resp.status_code == 200
    data = resp.json()["tools"]
    
    # Check for expected tools
    tool_ids = [t["id"] for t in data]
    assert "echo" in tool_ids
    assert "media_v2" in tool_ids
    assert "chat_service" in tool_ids
    assert "canvas_stream" in tool_ids
    
    # Check completeness rule: at least 4 tools
    assert len(tool_ids) >= 4
