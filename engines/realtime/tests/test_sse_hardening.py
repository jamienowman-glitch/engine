"""Tests for SSE Transport Hardening (Step 4)."""
import os
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from engines.chat.service.server import app
from engines.realtime.isolation import registry
from engines.identity.jwt_service import default_jwt_service

client = TestClient(app)

@pytest.fixture
def mock_jwt_secret():
    with patch.dict(os.environ, {"AUTH_JWT_SIGNING": "test-secret-key-123"}):
        yield "test-secret-key-123"

@pytest.fixture
def auth_headers(mock_jwt_secret):
    svc = default_jwt_service()
    token = svc.issue_token({
        "sub": "user-1",
        "default_tenant_id": "t_demo",
        "tenant_ids": ["t_demo"], 
        "role_map": {"t_demo": "member"}
    })
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": "t_demo",
        "X-Env": "dev"
    }

@pytest.fixture(autouse=True)
def cleanup():
    registry.clear()
    yield

def test_sse_chat_isolation(auth_headers):
    # Register verified thread
    registry.register_thread("t_demo", "th-1")
    registry.register_thread("t_other", "th-2")
    
    # Happy path
    with client.stream("GET", "/sse/chat/th-1", headers=auth_headers) as resp:
        assert resp.status_code == 200
    
    # Access denied to t_other
    # Note: verify_thread_access raises 404 for unknown/mismatch in our strict impl
    resp = client.get("/sse/chat/th-2", headers=auth_headers)
    assert resp.status_code == 404

    # Access unknown
    resp = client.get("/sse/chat/th-unknown", headers=auth_headers)
    assert resp.status_code == 404

def test_sse_canvas_isolation(auth_headers):
    registry.register_canvas("t_demo", "canvas-1")
    registry.register_canvas("t_other", "canvas-2")

    # Happy path
    with client.stream("GET", "/sse/canvas/canvas-1", headers=auth_headers) as resp:
        assert resp.status_code == 200

    # Access denied
    resp = client.get("/sse/canvas/canvas-2", headers=auth_headers)
    assert resp.status_code == 404

def test_sse_streamevent_structure(auth_headers):
    """Verify SSE yields proper StreamEvent JSON."""
    registry.register_canvas("t_demo", "canvas-active")
    
    # We need to simulate a message on the bus to see output.
    # Since we can't easily inject into the running bus of the TestClient process 
    # (unless we share the bus instance, which we do: engines.chat.service.transport_layer.bus)
    
    from engines.chat.service.transport_layer import bus
    from engines.chat.contracts import Message, Contact
    from datetime import datetime
    
    # Start stream
    with client.stream("GET", "/sse/canvas/canvas-active", headers=auth_headers) as response:
        # Publish event
        bus.add_message("canvas-active", Message(
            id="evt-1",
            thread_id="canvas-active",
            sender=Contact(id="user-1"),
            text='{"kind": "canvas_commit", "rev": 1}',
            role="system",
            created_at=datetime.utcnow()
        ))
        
        # Read stream
        # SSE iterator yields lines.
        # We look for "data: {...}"
        found = False
        for line in response.iter_lines():
            if line.startswith("data: "):
                import json
                payload = json.loads(line[6:])
                assert payload["type"] == "canvas_commit"
                assert payload["routing"]["tenant_id"] == "t_demo"
                found = True
                break
        assert found
