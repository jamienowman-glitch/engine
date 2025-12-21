"""Tests for Cancellation (Step 8)."""
import pytest
from unittest.mock import patch
import os
from fastapi.testclient import TestClient
from engines.chat.service.server import app
from engines.control.cancellation import register_run, router
from engines.common.identity import RequestContext
from engines.identity.jwt_service import default_jwt_service

# Include the router in the app for testing if not already autowired.
# engines.chat.service.server.app usually includes routers. 
# If not, we might need to include it manually or test router in isolation.
# For safety, let's include it.
app.include_router(router)

client = TestClient(app)

@pytest.fixture
def mock_jwt_secret():
    with patch.dict(os.environ, {"AUTH_JWT_SIGNING": "secret"}):
        yield "secret"

@pytest.fixture
def auth_headers(mock_jwt_secret):
    svc = default_jwt_service()
    token = svc.issue_token({
        "sub": "u1",
        "default_tenant_id": "t_demo",
        "tenant_ids": ["t_demo"],
        "role_map": {"t_demo": "member"}
    })
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": "t_demo",
        "X-Env": "dev"
    }

def test_cancel_run_success(auth_headers):
    # Setup
    register_run("run-123", "t_demo", "th-1")
    
    resp = client.post("/runs/run-123/cancel", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

def test_cancel_run_isolation(auth_headers):
    # Run belongs to other tenant
    register_run("run-456", "t_other", "th-2")
    
    resp = client.post("/runs/run-456/cancel", headers=auth_headers)
    assert resp.status_code == 404 # Should not leak existence

def test_cancel_run_not_found(auth_headers):
    resp = client.post("/runs/run-unknown/cancel", headers=auth_headers)
    assert resp.status_code == 404
