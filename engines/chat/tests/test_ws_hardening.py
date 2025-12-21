"""Tests for WS Transport Hardening (Step 3)."""
import os
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from engines.chat.service.server import app
from engines.realtime.isolation import registry
from engines.identity.jwt_service import default_jwt_service

client = TestClient(app)


def _ws_headers(token: str, tenant_id: str = "t_demo", env: str = "dev"):
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": tenant_id,
        "X-Env": env,
        "X-User-Id": "u_test",
        "X-Request-Id": "req-ws",
    }

# Helper to mock secret for JWT signing in tests
@pytest.fixture
def mock_jwt_secret():
    with patch.dict(os.environ, {"AUTH_JWT_SIGNING": "test-secret-key-123"}):
        yield "test-secret-key-123"

@pytest.fixture
def auth_token(mock_jwt_secret):
    svc = default_jwt_service()
    # "create_token" was wrong, use "issue_token"
    payload = {
        "sub": "user-1",
        "default_tenant_id": "t_demo",
        "tenant_ids": ["t_demo"],
        "role_map": {"t_demo": "member"}
    }
    return svc.issue_token(payload)

@pytest.fixture(autouse=True)
def cleanup():
    registry.clear()
    yield

def test_ws_no_token_rejected(mock_jwt_secret):
    # Depending on how TestClient/Starlette handles WS rejection:
    # It might raise WebSocketDisconnect if the server closes handshake immediately.
    try:
        with client.websocket_connect("/ws/chat/th-1") as websocket:
            # If strictly accepted, this would pass.
            # But we expect 4003 Close.
            # receive_text might raise if closed.
            websocket.receive_text()
    except Exception as e:
        # Starlette WebSocketDisconnect 4003
        assert "4003" in str(e) or "WebSocketDisconnect" in str(type(e).__name__)
        return
    
    # If we got here, it didn't reject (Failure)
    pytest.fail("WebSocket should have rejected connection without token")

def test_ws_mismatched_tenant_rejected(auth_token, mock_jwt_secret):
    # Token is for t_demo
    # Thread belongs to t_other
    registry.register_thread("t_other", "th-secret")
    
    headers = _ws_headers(auth_token)
    try:
        with client.websocket_connect("/ws/chat/th-secret", headers=headers) as websocket:
            websocket.receive_text()
    except Exception as e:
         # 4003 or 403
         assert "4003" in str(e) or "WebSocketDisconnect" in str(type(e).__name__)
         return
    
    pytest.fail("Should have rejected access to t_other thread")

def test_ws_unknown_thread_rejected(auth_token, mock_jwt_secret):
    # Thread not in registry
    headers = _ws_headers(auth_token)
    try:
         with client.websocket_connect("/ws/chat/th-unknown", headers=headers) as websocket:
                websocket.receive_text()
    except Exception as e:
         assert "4003" in str(e) or "WebSocketDisconnect" in str(type(e).__name__)
         return

    pytest.fail("Should have rejected unknown thread")

def test_ws_happy_path(auth_token, mock_jwt_secret):
    # Register thread for t_demo
    registry.register_thread("t_demo", "th-valid")
    headers = _ws_headers(auth_token)
    with client.websocket_connect("/ws/chat/th-valid", headers=headers) as websocket:
        data = websocket.receive_json()
        assert data["type"] == "presence_state"
        assert data["data"]["status"] == "online"
        assert data["data"]["user_id"] == "user-1"
        assert data["routing"]["tenant_id"] == "t_demo"
        assert data["routing"]["env"] == "dev"
        assert data["meta"]["last_event_id"] is None

        # Send a message
        websocket.send_json({"type": "message", "text": "hello"})

        # We assume pipeline returns nothing synchronously in tests or we don't mock it yet.
        # But connection remains open.
        websocket.send_json({"type": "ping"})
        pong = websocket.receive_json()
        assert pong["type"] == "pong"
