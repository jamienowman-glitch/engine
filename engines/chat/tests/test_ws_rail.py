import json
import os
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from engines.chat.service import transport_layer
from engines.chat.service.ws_transport import router as ws_router
from engines.common.identity import RequestContext
from engines.identity.jwt_service import default_jwt_service, AuthContext
from engines.realtime.isolation import register_thread_resource
from engines.realtime.timeline import InMemoryTimelineStore, set_timeline_store

app = FastAPI()
app.include_router(ws_router)

client = TestClient(app)


def _hello_payload(ctx: RequestContext) -> dict:
    return {
        "type": "hello",
        "context": {
            "tenant_id": ctx.tenant_id,
            "mode": ctx.mode,
            "project_id": ctx.project_id,
            "request_id": ctx.request_id,
            "user_id": ctx.user_id,
            "surface_id": ctx.surface_id,
            "app_id": ctx.app_id,
        },
    }


def _ws_headers(token: str):
    return {
        "Authorization": f"Bearer {token}",
    }


@pytest.fixture
def mock_token():
    with patch.dict(os.environ, {"AUTH_JWT_SIGNING": "secret-test-key"}):
        svc = default_jwt_service()
        claims = {
            "sub": "u_test",
            "tenant_ids": ["t_test"],
            "default_tenant_id": "t_test",
            "role_map": {"t_test": "member"},
        }
        token = svc.issue_token(claims)
        yield token


@pytest.fixture(autouse=True)
def reset_bus_and_timeline():
    transport_layer.bus._impl = transport_layer.InMemoryBus()
    set_timeline_store(InMemoryTimelineStore({}))
    yield


def test_ws_auth_required():
    try:
        with client.websocket_connect("/ws/chat/thread-1") as websocket:
            ctx = RequestContext(
                tenant_id="t_test",
                mode="saas",
                project_id="p_chat",
                surface_id="surface-alpha",
                app_id="app-chat",
            )
            websocket.send_json(_hello_payload(ctx))
            websocket.receive_text()
    except WebSocketDisconnect as exc:
        assert exc.code == 4003


def test_ws_auth_success(mock_token):
    with patch.dict(os.environ, {"AUTH_JWT_SIGNING": "secret-test-key"}):
        register_thread_resource("t_test", "thread-1")
        ctx = RequestContext(
            tenant_id="t_test",
            mode="saas",
            project_id="p_chat",
            request_id="req-ws",
            user_id="u_test",
            surface_id="surface-alpha",
            app_id="app-chat",
        )
        with client.websocket_connect("/ws/chat/thread-1", headers=_ws_headers(mock_token)) as websocket:
            websocket.send_json(_hello_payload(ctx))
            data = websocket.receive_json()
            assert data["type"] == "presence_state"
            assert data["data"]["user_id"] == "u_test"


def test_ws_message_flow(mock_token):
    thread_id = "thread-flow"
    with patch.dict(os.environ, {"AUTH_JWT_SIGNING": "secret-test-key"}):
        register_thread_resource("t_test", thread_id)
        ctx = RequestContext(
            tenant_id="t_test",
            mode="saas",
            project_id="p_chat",
            request_id="req-flow",
            user_id="u_test",
            surface_id="surface-alpha",
            app_id="app-chat",
        )
        with client.websocket_connect(
            f"/ws/chat/{thread_id}", headers=_ws_headers(mock_token)
        ) as websocket:
            websocket.send_json(_hello_payload(ctx))
            websocket.receive_json()  # presence

            websocket.send_json({"type": "ping"})
            assert websocket.receive_json()["type"] == "pong"


def test_ws_heartbeat_ping(mock_token):
    with patch.dict(os.environ, {"AUTH_JWT_SIGNING": "secret-test-key"}):
        register_thread_resource("t_test", "thread-hb")
        ctx = RequestContext(
            tenant_id="t_test",
            mode="saas",
            project_id="p_chat",
            request_id="req-hb",
            user_id="u_test",
            surface_id="surface-alpha",
            app_id="app-chat",
        )
        with client.websocket_connect("/ws/chat/thread-hb", headers=_ws_headers(mock_token)) as websocket:
             websocket.send_json(_hello_payload(ctx))
             websocket.receive_json() # presence
             
             websocket.send_json({"type": "ping"})
             resp = websocket.receive_json()
             assert resp["type"] == "pong"
