import asyncio
import json

from fastapi.testclient import TestClient

from engines.chat.contracts import Contact, Message
from engines.chat.service import server
from engines.chat.service.sse_transport import event_stream
from engines.chat.service.transport_layer import bus
from engines.common.identity import RequestContext
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

def _parse_event_chunk(chunk: str):
    event = {}
    for raw in chunk.splitlines():
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        event[key.strip()] = value.strip()
    return event


async def _collect_event_from_stream(thread_id: str, request_context: RequestContext, last_event_id: str | None):
    stream = event_stream(thread_id, request_context, last_event_id=last_event_id)
    try:
        chunk = await stream.__anext__()
        return chunk
    finally:
        await stream.aclose()


def test_sse_event_stream_resume():
    thread_id = "thread-sse-1"
    register_thread_resource("t_alpha", thread_id)
    first = _add_message(thread_id, "user-alpha", "first", "msg-first")
    second = _add_message(thread_id, "user-beta", "second", "msg-second")

    context = RequestContext(request_id="trace-sse-1",
        tenant_id="t_alpha",
        env="dev",
        user_id="user-alpha",
    )

    chunk = asyncio.run(
        _collect_event_from_stream(thread_id, context, last_event_id=first.id)
    )
    event = _parse_event_chunk(chunk)
    payload = json.loads(event["data"])
    assert payload["event_id"] == second.id
    assert payload["trace_id"] == context.request_id
    assert payload["meta"]["last_event_id"] == second.id


def test_sse_rejects_missing_auth(jwt_issuer):
    thread_id = "thread-sse-2"
    register_thread_resource("t_alpha", thread_id)
    client = TestClient(server.app)
    headers = {"X-Tenant-Id": "t_alpha", "X-Env": "dev"}
    response = client.get(f"/sse/chat/{thread_id}", headers=headers)
    assert response.status_code == 401


def test_sse_rejects_missing_env(jwt_issuer):
    thread_id = "thread-sse-4"
    register_thread_resource("t_alpha", thread_id)
    token = jwt_issuer(tenant_id="t_alpha", user_id="user-alpha")
    client = TestClient(server.app)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": "t_alpha",
    }
    # Missing X-Env header should trigger RequestContext rejection
    response = client.get(f"/sse/chat/{thread_id}", headers=headers)
    assert response.status_code == 400


def test_sse_rejects_cross_tenant(jwt_issuer):
    thread_id = "thread-sse-3"
    register_thread_resource("t_alpha", thread_id)
    token = jwt_issuer(tenant_id="t_beta", user_id="user-beta")
    client = TestClient(server.app)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": "t_alpha",
        "X-Env": "dev",
    }
    response = client.get(f"/sse/chat/{thread_id}", headers=headers)
    assert response.status_code == 403


def test_sse_rejects_unregistered_thread(jwt_issuer):
    thread_id = "thread-sse-missing"
    token = jwt_issuer(tenant_id="t_alpha", user_id="user-alpha")
    client = TestClient(server.app)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": "t_alpha",
        "X-Env": "dev",
    }
    response = client.get(f"/sse/chat/{thread_id}", headers=headers)
    assert response.status_code == 404
