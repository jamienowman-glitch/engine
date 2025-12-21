import pytest
from fastapi.testclient import TestClient
from engines.chat.service.server import create_app

def test_canvas_and_feature_flags_mounted():
    app = create_app()
    client = TestClient(app)
    
    headers = {"X-Tenant-Id": "t_test", "X-Env": "dev"}
    
    # Check Canvas Stream
    # L1-T2: /sse/canvas/{canvas_id} should exist (403/401) not 404
    resp = client.get("/sse/canvas/test-canvas-id", headers=headers)
    # If mounted and auth guarded, it returns 401 or 403.
    # If not mounted, it returns 404.
    assert resp.status_code in [401, 403], f"Expected 401/403 for Canvas Stream, got {resp.status_code}"
    
    # Check Feature Flags
    # L1-T2: /feature-flags should exist (401/403) not 404
    resp = client.get("/feature-flags", headers=headers)
    assert resp.status_code in [401, 403], f"Expected 401/403 for Feature Flags, got {resp.status_code}"

def test_feature_flags_requires_auth():
    # L3-T2 requirement
    app = create_app()
    client = TestClient(app)
    resp = client.get("/feature-flags")
    assert resp.status_code in [401, 403]
