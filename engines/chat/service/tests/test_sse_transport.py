import asyncio
import json
import os
from unittest.mock import patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("BUDGET_BACKEND", "filesystem")
os.environ.setdefault("BUDGET_BACKEND_FS_DIR", "/tmp/budget-test")

from engines.chat.contracts import Contact
from engines.chat.service import transport_layer
from engines.chat.service.http_transport import register_error_handlers
from engines.chat.service.sse_transport import _chat_stream_with_resume, _sse_context, router as sse_router
from engines.chat.service.transport_layer import publish_message
from engines.common.identity import RequestContext
from engines.identity.ticket_service import issue_ticket
from engines.realtime.isolation import register_thread_resource
from engines.realtime.timeline import InMemoryTimelineStore, set_timeline_store
from tests.chat_store_stub import install_chat_store_stub


app = FastAPI()
register_error_handlers(app)
app.include_router(sse_router)
@app.get("/sse/context-probe")
async def sse_context_probe(request_context: RequestContext = Depends(_sse_context)):
    return {"tenant": request_context.tenant_id}

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_bus_and_timeline():
    transport_layer.bus._impl = transport_layer.InMemoryBus()
    shared_storage: dict[str, list] = {}
    set_timeline_store(InMemoryTimelineStore(shared_storage))
    yield


@pytest.fixture(autouse=True)
def fake_chat_store(monkeypatch):
    return install_chat_store_stub(monkeypatch)


def _parse_event_chunk(chunk: str):
    event = {}
    for raw in chunk.splitlines():
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        event[key.strip()] = value.strip()
    return event


async def _collect_event_chunks(
    thread_id: str, request_context: RequestContext, last_event_id: str | None, count: int = 1
):
    stream = _chat_stream_with_resume(thread_id, request_context, last_event_id=last_event_id)
    chunks = []
    try:
        for _ in range(count):
            chunks.append(await stream.__anext__())
        return chunks
    finally:
        await stream.aclose()


def test_sse_event_stream_resume():
    thread_id = "thread-sse-1"
    register_thread_resource("t_alpha", thread_id)
    ctx = RequestContext(
        tenant_id="t_alpha",
        mode="saas",
        project_id="p_chat",
        request_id="trace-sse-1",
        user_id="user-alpha",
    )
    sender = Contact(id="user-alpha")
    first = publish_message(thread_id, sender, "first", context=ctx)
    second = publish_message(thread_id, sender, "second", context=ctx)

    chunks = asyncio.run(
        _collect_event_chunks(thread_id, ctx, last_event_id=first.id, count=2)
    )
    resume_chunk, data_chunk = chunks
    resume_event = _parse_event_chunk(resume_chunk)
    resume_payload = json.loads(resume_event["data"])
    assert resume_event["event"] == "resume_cursor"
    assert resume_payload["data"]["cursor"] == second.id

    event = _parse_event_chunk(data_chunk)
    payload = json.loads(event["data"])
    assert payload["event_id"] == second.id
    assert payload["trace_id"] == ctx.request_id
    assert payload["meta"]["last_event_id"] == second.id


def test_sse_rejects_missing_auth(jwt_issuer):
    thread_id = "thread-sse-unauth"
    register_thread_resource("t_alpha", thread_id)
    headers = {
        "X-Tenant-Id": "t_alpha",
        "X-Mode": "saas",
        "X-Project-Id": "p_chat",
        "X-Request-Id": "req-sse-unauth",
        "X-Surface-Id": "surf",
        "X-App-Id": "app",
    }
    with client.stream("GET", f"/sse/chat/{thread_id}", headers=headers) as response:
        assert response.status_code == 401
        response.read()
        payload = response.json()
        assert payload["error"]["code"] == "auth.ticket_missing"
        assert payload["error"]["http_status"] == 401


def test_sse_rejects_cross_tenant(jwt_issuer):
    thread_id = "thread-sse-3"
    register_thread_resource("t_alpha", thread_id)
    token = jwt_issuer(tenant_id="t_beta", user_id="user-beta")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": "t_alpha",
        "X-Mode": "saas",
        "X-Project-Id": "p_chat",
        "X-Request-Id": "req-sse-cross",
        "X-App-Id": "app",
    }
    with client.stream("GET", f"/sse/chat/{thread_id}", headers=headers) as response:
        assert response.status_code == 403
        response.read()
        payload = response.json()
        assert payload["error"]["code"] == "auth.tenant_mismatch"
        assert payload["error"]["http_status"] == 403


def test_sse_accepts_ticket_without_auth():
    thread_id = "thread-sse-ticket"
    register_thread_resource("t_alpha", thread_id)
    with patch.dict(os.environ, {"ENGINES_TICKET_SECRET": "ticket-secret"}):
        token = issue_ticket(
            {
                "tenant_id": "t_alpha",
                "mode": "saas",
                "project_id": "p_chat",
                "request_id": "req-ticket-sse",
                "user_id": "user-alpha",
            }
        )
        response = client.get(f"/sse/context-probe?ticket={token}")
        assert response.status_code == 200


def test_sse_invalid_ticket_envelope():
    thread_id = "thread-sse-ticket-invalid"
    register_thread_resource("t_alpha", thread_id)
    with patch.dict(os.environ, {"ENGINES_TICKET_SECRET": "ticket-secret"}):
        response = client.get(f"/sse/chat/{thread_id}?ticket=invalid-token")
    assert response.status_code == 401
    response.read()
    payload = response.json()
    assert payload["error"]["code"] == "auth.ticket_invalid"
    assert payload["error"]["http_status"] == 401


def test_sse_rejects_unregistered_thread(jwt_issuer):
    thread_id = "thread-sse-missing"
    token = jwt_issuer(tenant_id="t_alpha", user_id="user-alpha")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": "t_alpha",
        "X-Mode": "saas",
        "X-Project-Id": "p_chat",
        "X-Request-Id": "req-sse-missing",
        "X-Surface-Id": "surf",
        "X-App-Id": "app",
    }
    with client.stream("GET", f"/sse/chat/{thread_id}", headers=headers) as response:
        assert response.status_code == 404


def test_sse_invalid_cursor_envelope(jwt_issuer):
    thread_id = "thread-sse-cursor-invalid"
    register_thread_resource("t_alpha", thread_id)
    token = jwt_issuer(tenant_id="t_alpha", user_id="user-alpha")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": "t_alpha",
        "X-Mode": "saas",
        "X-Project-Id": "p_chat",
        "X-Request-Id": "req-sse-cursor",
        "X-Surface-Id": "surf",
        "X-App-Id": "app",
        "Last-Event-ID": "nonexistent",
    }
    response = client.get(f"/sse/chat/{thread_id}", headers=headers)
    assert response.status_code == 410
    response.read()
    payload = response.json()
    assert payload["error"]["code"] == "chat.cursor_invalid"
    assert payload["error"]["http_status"] == 410
