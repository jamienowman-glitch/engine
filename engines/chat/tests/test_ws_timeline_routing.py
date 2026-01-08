"""Tests for WS timeline routing hardening (ENG-2)."""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from engines.chat.service import transport_layer
from engines.chat.service.ws_transport import router as ws_router
from engines.identity.jwt_service import default_jwt_service
from engines.realtime.isolation import registry
from engines.realtime.timeline import InMemoryTimelineStore, set_timeline_store

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
) -> dict:
    payload = {
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
    }
    if last_event_id:
        payload["last_event_id"] = last_event_id
    return payload


def _ws_headers(token: str) -> dict:
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


@pytest.fixture
def mock_jwt_secret():
    with patch.dict(os.environ, {"AUTH_JWT_SIGNING": "test-secret-key"}):
        yield "test-secret-key"


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


def test_ws_missing_event_stream_route(auth_token, mock_jwt_secret, monkeypatch):
    registry.register_thread("t_demo", "th-missing")
    headers = _ws_headers(auth_token)

    def _raise_missing_route():
        raise RuntimeError(
            "No route configured for event_stream. "
            "Create a route via /routing/routes with backend_type='filesystem' or 'firestore'."
        )

    monkeypatch.setattr(
        "engines.chat.service.ws_transport.get_timeline_store",
        _raise_missing_route,
    )

    with client.websocket_connect("/ws/chat/th-missing", headers=headers) as websocket:
        websocket.send_json(_hello_payload("t_demo"))
        _assert_ws_error(websocket, "event_stream.missing_route", 503)


def test_ws_invalid_cursor_still_produces_410(auth_token, mock_jwt_secret):
    registry.register_thread("t_demo", "th-invalid")
    headers = _ws_headers(auth_token)

    with client.websocket_connect("/ws/chat/th-invalid", headers=headers) as websocket:
        websocket.send_json(_hello_payload("t_demo", last_event_id="unknown-cursor"))
        _assert_ws_error(websocket, "chat.cursor_invalid", 410)
