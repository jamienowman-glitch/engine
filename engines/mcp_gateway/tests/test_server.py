import pytest
from fastapi.testclient import TestClient
from engines.mcp_gateway.server import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "mcp_gateway"
    assert "time" in data
    assert data["status"] == "ok"

def test_identity_wiring_success():
    headers = {
        "X-Tenant-Id": "t_demo",
        "X-Mode": "lab",
        "X-Project-Id": "p_123",
        "X-User-Id": "u_test",
        "X-Surface-Id": "s_test",
        "X-App-Id": "a_test"
    }
    response = client.get("/debug/identity", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == "t_demo"
    assert data["mode"] == "lab"
    assert data["user_id"] == "u_test"

def test_identity_wiring_failure_missing_mode():
    headers = {
        "X-Tenant-Id": "t_demo",
        # Missing X-Mode
        "X-Project-Id": "p_123",
    }
    response = client.get("/debug/identity", headers=headers)
    # The RequestContextBuilder raises ValueError, which is caught by error handlers if wired,
    # or bubbles up. Our error_response / common error handlers usually map HTTPException.
    # But RequestContextBuilder raises ValueError for missing headers inside `from_headers` 
    # and get_request_context catches it and raises HTTPException(400).
    # So we expect 400.
    assert response.status_code == 400
    data = response.json()
    # Canonical error envelope check
    assert "error" in data
    assert data["error"]["http_status"] == 400

def test_identity_wiring_failure_invalid_mode():
    headers = {
        "X-Tenant-Id": "t_demo",
        "X-Mode": "invalid_mode",
        "X-Project-Id": "p_123",
    }
    response = client.get("/debug/identity", headers=headers)
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
