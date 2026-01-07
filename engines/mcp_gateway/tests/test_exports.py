import io
import csv
import pytest
from unittest.mock import MagicMock
import sys

# Mock Feature Flags again (copy paste setup or move to conftest if time permitted)
# Just quick mock here
mock_ff_repo = MagicMock()
mock_ff_repo.feature_flag_repo = MagicMock()
sys.modules["engines.feature_flags"] = MagicMock()
sys.modules["engines.feature_flags.repository"] = mock_ff_repo
sys.modules["engines.feature_flags.service"] = MagicMock()
sys.modules["engines.feature_flags.routes"] = MagicMock()

# Mock Firearms
mock_firearms_svc = MagicMock()
mock_firearms_svc.repo.get_binding.return_value = None # Default no binding
sys.modules["engines.firearms"] = MagicMock()
sys.modules["engines.firearms.service"] = MagicMock()
sys.modules["engines.firearms.service"].get_firearms_service.return_value = mock_firearms_svc

from fastapi.testclient import TestClient
from engines.mcp_gateway import server

def test_export_tools():
    client = TestClient(server.app)
    resp = client.get("/exports/tools")
    assert resp.status_code == 200
    text = resp.text
    assert "tool_id\tname\tsummary" in text
    assert "echo" in text
    assert "Chat Service" in text

def test_export_policies():
    client = TestClient(server.app)
    headers = {
        "X-Tenant-Id": "t_demo",
        "X-Mode": "lab",
        "X-Project-Id": "p1",
        "X-Surface-Id": "s1",
        "X-App-Id": "a1"
    }
    
    # Needs valid context for firearm binding check
    # We might need to mock get_firearms_service in tsv_export
    # but let's see if it runs with default mocks (likely empty binding)
    
    resp = client.get("/exports/policies", headers=headers)
    assert resp.status_code == 200
    text = resp.text
    assert "tool_id\tscope_name\trequires_firearms" in text
    # Should show Echo scopes
    assert "echo\techo.ping" in text
