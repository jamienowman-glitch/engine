import pytest
from fastapi.testclient import TestClient
from engines.mcp_gateway.server import app

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

def test_policy_enforcement_safe():
    # Echo is safe by default
    payload = {
        "tool_id": "echo",
        "scope_name": "echo.ping",
        "arguments": {}
    }
    response = client.post("/tools/call", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 200

def test_policy_enforcement_dangerous_blocked():
    # Configure policy to make echo.echo dangerous
    from engines.policy.service import get_policy_service, PolicyAttachment, Requirements
    
    att = PolicyAttachment(scopes={
        "echo.echo.echo": Requirements(firearms=True) # key format match? tool_id.scope_name -> "echo.echo.echo" ? 
        # inventory id is "echo", scope name is "echo.echo".
        # PolicyService uses {tool_id}.{scope_name} -> "echo.echo.echo"
    })
    
    # Wait, in echo.py: tool.id="echo", scope.name="echo.echo".
    # so full key is "echo.echo.echo".
    
    get_policy_service().set_policy("global", att)
    
    payload = {
        "tool_id": "echo",
        "scope_name": "echo.echo",
        "arguments": {"message": "danger"}
    }
    response = client.post("/tools/call", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "firearms.required"

def test_policy_enforcement_dangerous_allowed():
    # Send mock grant (simulated)
    headers = dict(AUTH_HEADERS)
    headers["X-Firearms-Grant"] = "granted"
    
    payload = {
        "tool_id": "echo",
        "scope_name": "echo.echo",
        "arguments": {"message": "danger"}
    }
    response = client.post("/tools/call", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["result"]["message"] == "danger"
    
    # Teardown policy
    from engines.policy.service import get_policy_service
    get_policy_service()._attachments.clear()
