import pytest
from fastapi.testclient import TestClient
from engines.chat.service.server import create_app

def test_canvas_and_feature_flags_mounted():
    app = create_app()
    client = TestClient(app)
    
    # Check Feature Flags mount (should be 401/403 not 404)
    # 404 means not mounted. 401/403 means mounted but rejected by auth/tenancy (which is correct behavior here)
    resp = client.get("/feature-flags")
    assert resp.status_code in [401, 403], f"Expected 401/403 (Mounted), got {resp.status_code}"
    
    # Check Canvas SSE mount
    resp = client.get("/sse/canvas/test-canvas-id")
    assert resp.status_code in [401, 403], f"Expected 401/403 (Mounted), got {resp.status_code}"

def test_feature_flags_requires_auth():
    # For L3-T2 later
    app = create_app()
    client = TestClient(app)
    resp = client.get("/feature-flags")
    assert resp.status_code == 403 or resp.status_code == 401
