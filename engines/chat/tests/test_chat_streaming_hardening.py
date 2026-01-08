import asyncio
import json
import os
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.chat.contracts import Contact
from engines.chat.service import transport_layer
from engines.chat.service.sse_transport import _chat_stream_with_resume, router as sse_router
from engines.chat.service.http_transport import register_error_handlers
from engines.chat.service.transport_layer import publish_message
from engines.chat.store_service import ChatMessageRecord
from engines.common.error_envelope import cursor_invalid_error
from engines.common.identity import RequestContext
from engines.identity.jwt_service import default_jwt_service
from engines.identity.models import App, Surface
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.state import set_identity_repo
from engines.realtime.isolation import registry

os.environ.setdefault("AUTH_JWT_SIGNING", "sse-secret")


class FakeChatStore:
    def __init__(self) -> None:
        self._threads: Dict[str, List[ChatMessageRecord]] = defaultdict(list)

    def append_message(self, thread_id: str, text: str, role: str, sender_id: str) -> ChatMessageRecord:
        timestamp = datetime.now(timezone.utc).isoformat()
        record = ChatMessageRecord(
            message_id=uuid.uuid4().hex,
            thread_id=thread_id,
            text=text,
            role=role,
            sender_id=sender_id,
            cursor=uuid.uuid4().hex,
            timestamp=timestamp,
        )
        self._threads[thread_id].append(record)
        return record

    def list_messages(self, thread_id: str, after_cursor: Optional[str] = None, limit: int = 100) -> List[ChatMessageRecord]:
        events = self._threads.get(thread_id, [])
        if after_cursor:
            for idx, rec in enumerate(events):
                if rec.cursor == after_cursor:
                    return events[idx + 1 : idx + 1 + limit]
            raise cursor_invalid_error(after_cursor, domain="chat")
        return events[:limit]

    def latest_cursor(self, thread_id: str) -> Optional[str]:
        events = self._threads.get(thread_id)
        if not events:
            return None
        return events[-1].cursor


def _auth_token(tenant_id: str = "t_demo", user_id: str = "user-1") -> str:
    svc = default_jwt_service()
    claims = {
        "sub": user_id,
        "default_tenant_id": tenant_id,
        "tenant_ids": [tenant_id],
        "role_map": {tenant_id: "member"},
    }
    return svc.issue_token(claims)


def _sse_headers(
    tenant_id: str = "t_demo",
    project_id: str = "p_chat",
    app_id: str = "app-chat",
    surface_id: str = "surface-alpha",
    mode: str = "lab",
) -> Dict[str, str]:
    headers = {
        "Authorization": f"Bearer {_auth_token(tenant_id=tenant_id)}",
        "X-Tenant-Id": tenant_id,
        "X-Mode": mode,
        "X-Project-Id": project_id,
        "X-Surface-Id": surface_id,
    }
    if app_id:
        headers["X-App-Id"] = app_id
    return headers


def _parse_sse_chunk(chunk: str) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    for raw in chunk.splitlines():
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def _read_sse_chunk(response: TestClient) -> str:
    buffer: List[str] = []
    for line in response.iter_lines(decode_unicode=True):
        if line == "":
            break
        buffer.append(line)
    return "\n".join(buffer)


@pytest.fixture(autouse=True)
def stub_nexus_backend(monkeypatch):
    class _StubBackend:
        def write_snippet(self, *args, **kwargs):
            return None
    monkeypatch.setattr("engines.chat.pipeline.get_backend", lambda: _StubBackend())


@pytest.fixture
def sse_client(monkeypatch) -> Tuple[TestClient, FakeChatStore]:
    registry.clear()
    transport_layer.bus._impl = transport_layer.InMemoryBus()
    identity_repo = InMemoryIdentityRepository()
    tenant = "t_demo"
    surface = Surface(tenant_id=tenant, name="default")
    identity_repo.create_surface(surface)
    app_record = App(tenant_id=tenant, name="app-chat")
    identity_repo.create_app(app_record)
    set_identity_repo(identity_repo)
    store = FakeChatStore()

    monkeypatch.setattr("engines.chat.service.sse_transport.chat_store_or_503", lambda ctx: store)
    monkeypatch.setattr("engines.chat.service.transport_layer.chat_store_or_503", lambda ctx: store)

    app = FastAPI()
    register_error_handlers(app)
    app.include_router(sse_router)
    client = TestClient(app, raise_server_exceptions=False)
    return client, store


def _process_message(thread_id: str, text: str, context: RequestContext) -> None:
    publish_message(thread_id, Contact(id=context.user_id or "user-1"), text, context=context)


def _build_request_context() -> RequestContext:
    return RequestContext(
        tenant_id="t_demo",
        env="dev",
        project_id="p_chat",
        request_id=str(uuid.uuid4()),
        user_id="user-1",
        surface_id="surface-alpha",
        app_id="app-chat",
        mode="lab",
    )


def test_sse_missing_app_id_rejected(sse_client):
    client, _ = sse_client
    thread_id = "thread-sse"
    registry.register_thread("t_demo", thread_id)
    headers = _sse_headers(app_id="")
    resp = client.get(f"/sse/chat/{thread_id}", headers=headers)
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"]["code"] == "auth.app_missing"
    assert payload["error"]["http_status"] == 400


def test_sse_missing_mode_rejected(sse_client):
    client, _ = sse_client
    thread_id = "thread-sse-missing-mode"
    registry.register_thread("t_demo", thread_id)
    headers = _sse_headers()
    headers.pop("X-Mode", None)
    resp = client.get(f"/sse/chat/{thread_id}", headers=headers)
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"]["code"] == "auth.mode_missing"
    assert payload["error"]["http_status"] == 400


def test_sse_missing_project_id_rejected(sse_client):
    client, _ = sse_client
    thread_id = "thread-sse-missing-project"
    registry.register_thread("t_demo", thread_id)
    headers = _sse_headers()
    headers.pop("X-Project-Id", None)
    resp = client.get(f"/sse/chat/{thread_id}", headers=headers)
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"]["code"] == "auth.project_missing"
    assert payload["error"]["http_status"] == 400


def test_sse_query_app_mismatch_rejected(sse_client):
    client, _ = sse_client
    thread_id = "thread-sse-mismatch"
    registry.register_thread("t_demo", thread_id)
    headers = _sse_headers()
    resp = client.get(f"/sse/chat/{thread_id}", headers=headers, params={"app_id": "other-app"})
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"]["code"] == "auth.context_mismatch"
    assert payload["error"]["http_status"] == 400


def test_sse_invalid_cursor_returns_410(sse_client):
    client, _ = sse_client
    thread_id = "thread-invalid-cursor"
    registry.register_thread("t_demo", thread_id)
    headers = _sse_headers()
    resp = client.get(f"/sse/chat/{thread_id}", headers=headers, params={"last_event_id": "missing-cursor"})
    assert resp.status_code == 410
    payload = resp.json()
    assert payload["error"]["code"] == "chat.cursor_invalid"
    assert payload["error"]["http_status"] == 410


def test_sse_resume_after_restart(sse_client):
    _, store = sse_client
    thread_id = "thread-sse-restart"
    registry.register_thread("t_demo", thread_id)
    context = _build_request_context()
    _process_message(thread_id, "first", context)
    last_cursor = store.latest_cursor(thread_id)
    _process_message(thread_id, "second", context)

    new_store = FakeChatStore()
    new_store._threads = {tid: list(records) for tid, records in store._threads.items()}

    async def collect_chunks():
        stream = _chat_stream_with_resume(
            thread_id=thread_id,
            request_context=context,
            last_event_id=last_cursor,
            store=new_store,
            validate_cursor=True,
        )
        chunks: List[str] = []
        try:
            for _ in range(2):
                chunks.append(await stream.__anext__())
            return chunks
        finally:
            await stream.aclose()

    resume_chunk, data_chunk = asyncio.run(collect_chunks())
    resume_event = _parse_sse_chunk(resume_chunk)
    resume_data = json.loads(resume_event["data"])
    assert resume_event["event"] == "resume_cursor"
    latest_cursor = new_store.latest_cursor(thread_id)
    assert resume_data["data"]["cursor"] == latest_cursor

    message_event = _parse_sse_chunk(data_chunk)
    message_data = json.loads(message_event["data"])
    assert message_data["data"]["text"] == "second"
