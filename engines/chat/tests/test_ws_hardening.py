"""Tests for WS Transport Hardening (Step 3)."""
import os
import pytest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.chat.service import transport_layer
from engines.chat.service.ws_transport import router as ws_router
from engines.realtime.isolation import registry
from engines.identity.jwt_service import default_jwt_service
from engines.realtime.timeline import InMemoryTimelineStore, set_timeline_store

os.environ.setdefault("BUDGET_BACKEND", "filesystem")
os.environ.setdefault("BUDGET_BACKEND_FS_DIR", "/tmp/budget-test")

app = FastAPI()
app.include_router(ws_router)
client = TestClient(app)


def _hello_payload(tenant_id: str, user_id: str = "user-1", request_id: str = "req-ws"):
    return {
        "type": "hello",
        "context": {
            "tenant_id": tenant_id,
            "mode": "saas",
            "project_id": "p_chat",
            "request_id": request_id,
            "user_id": user_id,
        },
    }


def _ws_headers(token: str):
    return {
        "Authorization": f"Bearer {token}",
    }


# Helper to mock secret for JWT signing in tests
@pytest.fixture
def mock_jwt_secret():
    with patch.dict(os.environ, {"AUTH_JWT_SIGNING": "test-secret-key-123"}):
        yield "test-secret-key-123"


@pytest.fixture
def auth_token(mock_jwt_secret):
    svc = default_jwt_service()
    payload = {
        "sub": "user-1",
        "default_tenant_id": "t_demo",
        "tenant_ids": ["t_demo"],
        "role_map": {"t_demo": "member"},
    }
    return svc.issue_token(payload)


@pytest.fixture(autouse=True)
def cleanup():
    registry.clear()
    transport_layer.bus._impl = transport_layer.InMemoryBus()
    set_timeline_store(InMemoryTimelineStore({}))
    yield


def test_ws_no_token_rejected(mock_jwt_secret):
    try:
        with client.websocket_connect("/ws/chat/th-1") as websocket:
            websocket.send_json(_hello_payload("t_demo"))
            websocket.receive_text()
    except Exception as e:
        assert "4003" in str(e) or "WebSocketDisconnect" in str(type(e).__name__)
        return
    pytest.fail("WebSocket should have rejected connection without token")


def test_ws_mismatched_tenant_rejected(auth_token, mock_jwt_secret):
    registry.register_thread("t_other", "th-secret")
    headers = _ws_headers(auth_token)
    try:
        with client.websocket_connect("/ws/chat/th-secret", headers=headers) as websocket:
            websocket.send_json(_hello_payload("t_demo"))
            websocket.receive_text()
    except Exception as e:
         assert "4003" in str(e) or "WebSocketDisconnect" in str(type(e).__name__)
         return
    pytest.fail("Should have rejected access to t_other thread")


def test_ws_unknown_thread_rejected(auth_token, mock_jwt_secret):
    headers = _ws_headers(auth_token)
    try:
         with client.websocket_connect("/ws/chat/th-unknown", headers=headers) as websocket:
                websocket.send_json(_hello_payload("t_demo"))
                websocket.receive_text()
    except Exception as e:
         assert "4003" in str(e) or "WebSocketDisconnect" in str(type(e).__name__)
         return

    pytest.fail("Should have rejected unknown thread")


def test_ws_happy_path(auth_token, mock_jwt_secret):
    registry.register_thread("t_demo", "th-valid")
    headers = _ws_headers(auth_token)
    with client.websocket_connect("/ws/chat/th-valid", headers=headers) as websocket:
        websocket.send_json(_hello_payload("t_demo"))
        data = websocket.receive_json()
        assert data["type"] == "presence_state"
        assert data["data"]["status"] == "online"
        assert data["data"]["user_id"] == "user-1"
        assert data["routing"]["tenant_id"] == "t_demo"
        assert data["routing"]["env"] == "dev"
        assert data["meta"]["last_event_id"] is None

        websocket.send_json({"type": "ping"})
        pong = websocket.receive_json()
        assert pong["type"] == "pong"
