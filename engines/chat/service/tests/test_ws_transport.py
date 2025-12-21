import pytest

from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from engines.chat.contracts import Contact, Message
from engines.chat.service import server
from engines.chat.service.transport_layer import bus
from engines.realtime.isolation import register_thread_resource


def _add_message(thread_id: str, owner: str, text: str, msg_id: str):
    msg = Message(
        id=msg_id,
        thread_id=thread_id,
        sender=Contact(id=owner),
        text=text,
        role="user",
    )
    bus.add_message(thread_id, msg)
    return msg


def test_ws_replays_messages_with_resume_cursor(jwt_issuer):
    thread_id = "thread-ws-1"
    register_thread_resource("t_alpha", thread_id)
    first = _add_message(thread_id, "user-alpha", "first", "msg-ws-first")
    second = _add_message(thread_id, "user-alpha", "second", "msg-ws-second")

    token = jwt_issuer(tenant_id="t_alpha", user_id="user-alpha")
    client = TestClient(server.app)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": "t_alpha",
        "X-Env": "dev",
        "X-Request-Id": "trace-ws-1",
    }

    with client.websocket_connect(
        f"/ws/chat/{thread_id}?last_event_id={first.id}",
        headers=headers,
    ) as ws:
        replay = ws.receive_json()
        assert replay["type"] == "user_message"
        assert replay["event_id"] == second.id
        assert replay["trace_id"] == "trace-ws-1"

        resume = ws.receive_json()
        assert resume["type"] == "resume_cursor"
        assert resume["data"]["cursor"] == second.id
        assert resume["meta"]["last_event_id"] == second.id

        presence = ws.receive_json()
        assert presence["type"] == "presence_state"


def test_ws_rejects_missing_auth(jwt_issuer):
    thread_id = "thread-ws-2"
    register_thread_resource("t_alpha", thread_id)
    client = TestClient(server.app)
    headers = {"X-Tenant-Id": "t_alpha", "X-Env": "dev"}
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/chat/{thread_id}", headers=headers):
            pass
    assert exc.value.code == 4003


def test_ws_rejects_cross_tenant(jwt_issuer):
    thread_id = "thread-ws-3"
    register_thread_resource("t_alpha", thread_id)
    token = jwt_issuer(tenant_id="t_beta", user_id="user-beta")
    client = TestClient(server.app)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": "t_alpha",
        "X-Env": "dev",
    }
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/chat/{thread_id}", headers=headers):
            pass
    assert exc.value.code == 4003


def test_ws_rejects_missing_env(jwt_issuer):
    thread_id = "thread-ws-4"
    register_thread_resource("t_alpha", thread_id)
    token = jwt_issuer(tenant_id="t_alpha", user_id="user-alpha")
    client = TestClient(server.app)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": "t_alpha",
    }
    # Intentionally omit X-Env to trigger RequestContext rejection
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/chat/{thread_id}", headers=headers):
            pass
    assert exc.value.code == 4003


def test_ws_rejects_unregistered_thread(jwt_issuer):
    thread_id = "thread-ws-5"
    token = jwt_issuer(tenant_id="t_alpha", user_id="user-alpha")
    client = TestClient(server.app)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": "t_alpha",
        "X-Env": "dev",
    }
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/chat/{thread_id}", headers=headers):
            pass
    assert exc.value.code == 4003
