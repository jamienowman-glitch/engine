"""Tests for WS Transport Hardening (Step 3)."""
import os
import pytest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from engines.chat.contracts import Contact
from engines.chat.service import transport_layer
from engines.chat.service.transport_layer import publish_message
from engines.chat.service.ws_transport import router as ws_router
from engines.common.identity import RequestContext
from engines.identity.jwt_service import default_jwt_service
from engines.identity.ticket_service import issue_ticket
from engines.realtime.isolation import register_thread_resource, registry
from engines.realtime.timeline import InMemoryTimelineStore, set_timeline_store
from tests.chat_store_stub import InMemoryChatStore

os.environ.setdefault("BUDGET_BACKEND", "filesystem")
os.environ.setdefault("BUDGET_BACKEND_FS_DIR", "/tmp/budget-test")

app = FastAPI()
app.include_router(ws_router)
client = TestClient(app)


def _hello_payload(
    tenant_id: str,
    user_id: str = "user-1",
    request_id: str = "req-ws",
    surface_id: str = "surface-alpha",
    app_id: str = "app-chat",
    last_event_id: str | None = None,
):
    return {
        "type": "hello",
        "context": {
            "tenant_id": tenant_id,
            "mode": "saas",
            "project_id": "p_chat",
            "request_id": request_id,
            "user_id": user_id,
            "surface_id": surface_id,
            "app_id": app_id,
        },
        **({"last_event_id": last_event_id} if last_event_id else {}),
    }


def _ws_headers(token: str):
    return {
        "Authorization": f"Bearer {token}",
    }


def _assert_ws_error(websocket, expected_code: str, expected_status: int):
    payload = websocket.receive_json()
    error = payload.get("error", {})
    assert error.get("code") == expected_code
    assert error.get("http_status") == expected_status
    with pytest.raises(WebSocketDisconnect) as exc:
        websocket.receive_text()
    assert exc.value.code == 4003


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
    with client.websocket_connect("/ws/chat/th-1") as websocket:
        websocket.send_json(_hello_payload("t_demo"))
        _assert_ws_error(websocket, "auth.ticket_missing", 401)


def test_ws_mismatched_tenant_rejected(auth_token, mock_jwt_secret):
    registry.register_thread("t_other", "th-secret")
    headers = _ws_headers(auth_token)
    with client.websocket_connect("/ws/chat/th-secret", headers=headers) as websocket:
        websocket.send_json(_hello_payload("t_demo"))
        _assert_ws_error(websocket, "chat.access_denied", 404)


def test_ws_hello_context_tenant_mismatch(auth_token, mock_jwt_secret):
    registry.register_thread("t_demo", "th-demo")
    headers = _ws_headers(auth_token)
    with client.websocket_connect("/ws/chat/th-demo", headers=headers) as websocket:
        websocket.send_json(_hello_payload("t_other", surface_id="surface-beta"))
        _assert_ws_error(websocket, "auth.tenant_mismatch", 401)


def test_ws_unknown_thread_rejected(auth_token, mock_jwt_secret):
    headers = _ws_headers(auth_token)
    with client.websocket_connect("/ws/chat/th-unknown", headers=headers) as websocket:
        websocket.send_json(_hello_payload("t_demo"))
        _assert_ws_error(websocket, "chat.access_denied", 404)


def test_ws_invalid_ticket_rejected(mock_jwt_secret):
    with patch.dict(os.environ, {"ENGINES_TICKET_SECRET": "ticket-secret"}):
        with client.websocket_connect("/ws/chat/th-1?ticket=invalid-token") as websocket:
            websocket.send_json(_hello_payload("t_demo"))
            _assert_ws_error(websocket, "auth.ticket_invalid", 401)


def test_ws_missing_mode_rejected(auth_token, mock_jwt_secret):
    thread_id = "th-missing-mode"
    registry.register_thread("t_demo", thread_id)
    headers = _ws_headers(auth_token)
    with client.websocket_connect(f"/ws/chat/{thread_id}", headers=headers) as websocket:
        payload = _hello_payload("t_demo")
        payload["context"].pop("mode", None)
        websocket.send_json(payload)
        _assert_ws_error(websocket, "auth.mode_missing", 400)


def test_ws_missing_project_rejected(auth_token, mock_jwt_secret):
    thread_id = "th-missing-project"
    registry.register_thread("t_demo", thread_id)
    headers = _ws_headers(auth_token)
    with client.websocket_connect(f"/ws/chat/{thread_id}", headers=headers) as websocket:
        payload = _hello_payload("t_demo")
        payload["context"].pop("project_id", None)
        websocket.send_json(payload)
        _assert_ws_error(websocket, "auth.project_missing", 400)


def test_ws_missing_app_rejected(auth_token, mock_jwt_secret):
    thread_id = "th-missing-app"
    registry.register_thread("t_demo", thread_id)
    headers = _ws_headers(auth_token)
    with client.websocket_connect(f"/ws/chat/{thread_id}", headers=headers) as websocket:
        payload = _hello_payload("t_demo")
        payload["context"].pop("app_id", None)
        websocket.send_json(payload)
        _assert_ws_error(websocket, "auth.app_missing", 400)


def test_ws_ticket_context_mismatch(mock_jwt_secret):
    thread_id = "th-ticket-mismatch"
    register_thread_resource("t_demo", thread_id)
    with patch.dict(os.environ, {"ENGINES_TICKET_SECRET": "ticket-secret"}):
        token = issue_ticket(
            {
                "tenant_id": "t_demo",
                "mode": "saas",
                "project_id": "p_chat",
                "app_id": "app-alpha",
            }
        )
        with client.websocket_connect(f"/ws/chat/{thread_id}") as websocket:
            payload = _hello_payload("t_demo", app_id="app-beta")
            payload["ticket"] = token
            websocket.send_json(payload)
            _assert_ws_error(websocket, "auth.context_mismatch", 400)


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


def test_ws_resume_after_restart(auth_token, mock_jwt_secret, monkeypatch):
    thread_id = "thread-ws-restart"
    register_thread_resource("t_demo", thread_id)
    shared_storage: dict[str, list] = {}
    set_timeline_store(InMemoryTimelineStore(shared_storage))

    store = InMemoryChatStore()
    monkeypatch.setattr(
        "engines.chat.service.transport_layer.chat_store_or_503",
        lambda ctx: store,
    )

    ctx = RequestContext(
        tenant_id="t_demo",
        env="dev",
        project_id="p_chat",
        request_id="trace-ws-restart",
        user_id="user-alpha",
        surface_id="surface-alpha",
        app_id="app-chat",
        mode="saas",
    )
    sender = Contact(id=ctx.user_id)
    first = publish_message(thread_id, sender, "first", context=ctx)
    second = publish_message(thread_id, sender, "second", context=ctx)

    transport_layer.bus._impl = transport_layer.InMemoryBus()
    set_timeline_store(InMemoryTimelineStore(shared_storage))

    app = FastAPI()
    app.include_router(ws_router)
    with TestClient(app) as restart_client:
        headers = _ws_headers(auth_token)
        with restart_client.websocket_connect(f"/ws/chat/{thread_id}", headers=headers) as websocket:
            websocket.send_json(
                _hello_payload(
                    ctx.tenant_id,
                    ctx.user_id,
                    ctx.request_id,
                    ctx.surface_id,
                    ctx.app_id or "app-chat",
                    last_event_id=first.id,
                )
            )
            replay = websocket.receive_json()
            assert replay["type"] == "chat_message"
            assert replay["event_id"] == second.id
            assert replay["trace_id"] == ctx.request_id

            resume = websocket.receive_json()
            assert resume["type"] == "resume_cursor"
            assert resume["data"]["cursor"] == second.id
            assert resume["meta"]["last_event_id"] == second.id

            presence = websocket.receive_json()
            assert presence["type"] == "presence_state"
