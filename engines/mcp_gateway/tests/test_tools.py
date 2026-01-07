import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from engines.mcp_gateway.server import app
from engines.mcp_gateway.inventory import get_inventory
from engines.media_v2.models import MediaAsset

client = TestClient(app)

# Headers with app/surface to avoid lookup
AUTH_HEADERS = {
    "X-Tenant-Id": "t_demo",
    "X-Mode": "lab",
    "X-Project-Id": "p_123",
    "X-User-Id": "u_test",
    "X-Surface-Id": "s_test",
    "X-App-Id": "a_test"
}

def test_tools_list():
    response = client.post("/tools/list", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    
    tools = {t["id"]: t for t in data["tools"]}
    assert "echo" in tools
    assert "media_v2" in tools
    
    echo_tool = tools["echo"]
    scope_names = {s["name"] for s in echo_tool["scopes"]}
    assert "echo.ping" in scope_names
    assert "echo.echo" in scope_names
    
    media_tool = tools["media_v2"]
    media_scopes = {s["name"] for s in media_tool["scopes"]}
    assert "media_v2.list" in media_scopes
    assert "media_v2.get" in media_scopes

def test_call_echo_ping():
    payload = {
        "tool_id": "echo",
        "scope_name": "echo.ping",
        "arguments": {}
    }
    response = client.post("/tools/call", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["result"]["message"] == "pong"

def test_call_echo_echo():
    payload = {
        "tool_id": "echo",
        "scope_name": "echo.echo",
        "arguments": {"message": "hello world"}
    }
    response = client.post("/tools/call", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["result"]["message"] == "hello world"

@patch("engines.mcp_gateway.tools.media_v2.get_media_service")
def test_call_media_list(mock_get_service):
    # Mock service
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service
    mock_service.list_assets.return_value = []
    
    payload = {
        "tool_id": "media_v2",
        "scope_name": "media_v2.list",
        "arguments": {}
    }
    response = client.post("/tools/call", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 200
    mock_service.list_assets.assert_called_once()
    assert response.json()["result"] == []

@patch("engines.mcp_gateway.tools.media_v2.get_media_service")
def test_call_media_get_found(mock_get_service):
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service
    
    asset = MediaAsset(
        id="asset_123",
        tenant_id="t_demo",
        env="lab",
        kind="video",
        source_uri="http://example.com/test.mp4"
    )
    mock_service.get_asset.return_value = asset
    
    payload = {
        "tool_id": "media_v2",
        "scope_name": "media_v2.get",
        "arguments": {"asset_id": "asset_123"}
    }
    response = client.post("/tools/call", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json()["result"]["id"] == "asset_123"

@patch("engines.mcp_gateway.tools.media_v2.get_media_service")
def test_call_media_get_not_found(mock_get_service):
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service
    mock_service.get_asset.return_value = None
    
    payload = {
        "tool_id": "media_v2",
        "scope_name": "media_v2.get",
        "arguments": {"asset_id": "asset_999"}
    }
    response = client.post("/tools/call", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 404
