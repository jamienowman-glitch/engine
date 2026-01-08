import os
import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

os.environ.setdefault("BUDGET_BACKEND", "filesystem")
os.environ.setdefault("BUDGET_BACKEND_FS_DIR", "/tmp/budget-test")

from engines.chat.contracts import Contact
from engines.chat.service import transport_layer
from engines.chat.service.ws_transport import router as ws_router
from engines.chat.service.transport_layer import publish_message
from engines.common.identity import RequestContext
from engines.realtime.isolation import register_thread_resource
from engines.realtime.timeline import InMemoryTimelineStore, set_timeline_store


app = FastAPI()
app.include_router(ws_router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_bus_and_timeline():
    transport_layer.bus._impl = transport_layer.InMemoryBus()
    shared_storage: dict[str, list] = {}
    set_timeline_store(InMemoryTimelineStore(shared_storage))
    yield


def _hello_payload(ctx: RequestContext, last_event_id: str | None = None) -> dict:
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
        "last_event_id": last_event_id,
    }


def test_ws_replays_messages_with_resume_cursor(jwt_issuer):
    thread_id = "thread-ws-1"
    register_thread_resource("t_alpha", thread_id)
    ctx = RequestContext(
        tenant_id="t_alpha",
        mode="saas",
        project_id="p_chat",
        request_id="trace-ws-1",
        user_id="user-alpha",
        surface_id="surface-alpha",
        app_id="app-chat",
    )
    sender = Contact(id="user-alpha")
    first = publish_message(thread_id, sender, "first", context=ctx)
    second = publish_message(thread_id, sender, "second", context=ctx)

    token = jwt_issuer(tenant_id="t_alpha", user_id="user-alpha")
    headers = {"Authorization": f"Bearer {token}"}
    with client.websocket_connect(f"/ws/chat/{thread_id}", headers=headers) as ws:
        ws.send_json(_hello_payload(ctx, last_event_id=first.id))

        replay = ws.receive_json()
        assert replay["type"] == "chat_message"
        assert replay["event_id"] == second.id
        assert replay["trace_id"] == ctx.request_id

        resume = ws.receive_json()
        assert resume["type"] == "resume_cursor"
        assert resume["data"]["cursor"] == second.id
        assert resume["meta"]["last_event_id"] == second.id

        presence = ws.receive_json()
        assert presence["type"] == "presence_state"


def test_ws_rejects_missing_auth():
    thread_id = "thread-ws-unauth"
    register_thread_resource("t_alpha", thread_id)
    ctx = RequestContext(
        tenant_id="t_alpha",
        mode="saas",
        project_id="p_chat",
        request_id="req-unauth",
        user_id="user-alpha",
        surface_id="surface-alpha",
        app_id="app-chat",
    )
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/chat/{thread_id}") as ws:
            ws.send_json(_hello_payload(ctx))
            ws.receive_json()
    assert exc.value.code == 4003


def test_ws_rejects_cross_tenant(jwt_issuer):
    thread_id = "thread-ws-cross"
    register_thread_resource("t_alpha", thread_id)
    ctx = RequestContext(
        tenant_id="t_alpha",
        mode="saas",
        project_id="p_chat",
        request_id="req-cross",
        user_id="user-beta",
        surface_id="surface-alpha",
        app_id="app-chat",
    )
    token = jwt_issuer(tenant_id="t_beta", user_id="user-beta")
    headers = {"Authorization": f"Bearer {token}"}
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/chat/{thread_id}", headers=headers) as ws:
            ws.send_json(_hello_payload(ctx))
            ws.receive_json()
    assert exc.value.code == 4003


def test_ws_rejects_invalid_mode(jwt_issuer):
    thread_id = "thread-ws-mode"
    register_thread_resource("t_alpha", thread_id)
    ctx = RequestContext(
        tenant_id="t_alpha",
        mode="saas",
        project_id="p_chat",
        request_id="req-mode",
        user_id="user-alpha",
        surface_id="surface-alpha",
        app_id="app-chat",
    )
    bad_context = {
        "tenant_id": ctx.tenant_id,
        "mode": "prod",
        "project_id": ctx.project_id,
        "request_id": ctx.request_id,
    }
    token = jwt_issuer(tenant_id="t_alpha", user_id="user-alpha")
    headers = {"Authorization": f"Bearer {token}"}
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/chat/{thread_id}", headers=headers) as ws:
            ws.send_json({"type": "hello", "context": bad_context})
            ws.receive_json()
    assert exc.value.code == 4003


def test_ws_rejects_unregistered_thread(jwt_issuer):
    thread_id = "thread-ws-missing"
    ctx = RequestContext(
        tenant_id="t_alpha",
        mode="saas",
        project_id="p_chat",
        request_id="req-missing",
        user_id="user-alpha",
        surface_id="surface-alpha",
        app_id="app-chat",
    )
    token = jwt_issuer(tenant_id="t_alpha", user_id="user-alpha")
    headers = {"Authorization": f"Bearer {token}"}
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/chat/{thread_id}", headers=headers) as ws:
            ws.send_json(_hello_payload(ctx))
            ws.receive_json()
    assert exc.value.code == 4003
