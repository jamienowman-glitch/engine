import os
import pytest
import json
import asyncio
import importlib
from unittest.mock import patch
from fastapi.testclient import TestClient
from engines.chat.service.http_transport import register_error_handlers
from engines.canvas_stream.router import (
    router as sse_router,
    _canvas_stream_with_resume,
)
_canvas_router_module = importlib.import_module("engines.canvas_stream.router")
from engines.canvas_stream.service import publish_canvas_event
from engines.identity.auth import get_auth_context, get_optional_auth_context
from engines.common.identity import get_request_context, RequestContext
from engines.identity.jwt_service import AuthContext
from engines.chat.service import transport_layer
from engines.realtime.timeline import InMemoryTimelineStore, set_timeline_store
from engines.kill_switch.service import KillSwitchService, set_kill_switch_service
from engines.kill_switch.repository import InMemoryKillSwitchRepository
from tests.chat_store_stub import install_chat_store_stub

from fastapi import FastAPI, Depends

app = FastAPI()
register_error_handlers(app)
app.include_router(sse_router)

# Use in-memory kill switch repository during tests to avoid Firestore calls.
set_kill_switch_service(KillSwitchService(repo=InMemoryKillSwitchRepository()))

client = TestClient(app)

# Mocks
async def mock_auth_ctx():
    return AuthContext(
        user_id="u_test",
        email="test@example.com",
        tenant_ids=["t_test"],
        default_tenant_id="t_test",
        role_map={"t_test": "member"}
    )

async def mock_req_ctx():
    return RequestContext(
        tenant_id="t_test",
        env="dev",
        mode="saas",
        project_id="p_chat",
        request_id="req-canvas-ctx",
        user_id="u_test",
    )


app.dependency_overrides[get_auth_context] = mock_auth_ctx
app.dependency_overrides[get_request_context] = mock_req_ctx
app.dependency_overrides[get_optional_auth_context] = mock_auth_ctx


@pytest.fixture(autouse=True)
def fake_chat_store(monkeypatch):
    return install_chat_store_stub(monkeypatch)


@pytest.fixture(autouse=True)
def reset_bus_and_timeline():
    transport_layer.bus._impl = transport_layer.InMemoryBus()
    set_timeline_store(InMemoryTimelineStore({}))
    yield


@pytest.fixture(autouse=True)
def override_canvas_request_context(monkeypatch):
    async def _canvas_request_context(*args, **kwargs):
        return RequestContext(
            tenant_id="t_test",
            env="dev",
            mode="saas",
            project_id="p_chat",
            request_id="req-canvas-ctx",
            user_id="u_test",
        )

    async def _canvas_optional_auth_ctx(*args, **kwargs):
        return AuthContext(
            user_id="u_test",
            email="test@example.com",
            tenant_ids=["t_test"],
            default_tenant_id="t_test",
            role_map={"t_test": "member"},
        )

    monkeypatch.setattr(
        _canvas_router_module,
        "get_request_context",
        _canvas_request_context,
    )
    monkeypatch.setattr(
        _canvas_router_module,
        "get_optional_auth_context",
        _canvas_optional_auth_ctx,
    )
    monkeypatch.setattr(
        _canvas_router_module,
        "get_auth_context",
        lambda *args, **kwargs: _canvas_optional_auth_ctx(),
    )
    yield


@pytest.fixture(autouse=True)
def stub_gate_chain(monkeypatch):
    class NoopGateChain:
        def run(self, *args, **kwargs):
            return None

    monkeypatch.setattr(
        "engines.nexus.hardening.gate_chain.get_gate_chain",
        lambda: NoopGateChain(),
    )
    monkeypatch.setattr(
        "engines.canvas_stream.service.get_gate_chain",
        lambda: NoopGateChain(),
    )
    yield


def _parse_event_chunk(chunk: str):
    event = {}
    for raw in chunk.splitlines():
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        event[key.strip()] = value.strip()
    return event


async def _collect_canvas_event_chunks(
    canvas_id: str,
    request_context: RequestContext,
    last_event_id: str | None,
    count: int = 1,
):
    stream = _canvas_stream_with_resume(
        canvas_id,
        request_context,
        last_event_id=last_event_id,
    )
    chunks = []
    try:
        for _ in range(count):
            chunks.append(await stream.__anext__())
        return chunks
    finally:
        try:
            await asyncio.wait_for(stream.aclose(), timeout=0.5)
        except asyncio.TimeoutError:
            pass

def test_sse_connect_and_stream():
    canvas_id = "canvas-1"
    ctx = RequestContext(
        tenant_id="t_test",
        env="dev",
        mode="saas",
        project_id="p_chat",
        request_id="req-canvas-connect",
        user_id="u_test",
    )
    evt = publish_canvas_event(canvas_id, "canvas_update", {"x": 10}, "u_test", ctx)

    chunks = asyncio.run(
        _collect_canvas_event_chunks(
            canvas_id,
            ctx,
            last_event_id=evt.id,
            count=1,
        )
    )
    resume_chunk = chunks[0]
    resume_event = _parse_event_chunk(resume_chunk)
    resume_payload = json.loads(resume_event["data"])
    assert resume_event["event"] == "resume_cursor"
    assert resume_payload["data"]["cursor"] == evt.id

def test_stream_canvas_auto_registers():
    """
    L1-T3: Verify that publishing an event registers the canvas, allowing SSE access.
    """
    canvas_id = "canvas-auto-reg-1"
    tenant_id = "t_test"
    
    # 1. Publish (should register)
    ctx = RequestContext(
        tenant_id=tenant_id,
        env="dev",
        mode="saas",
        project_id="p_chat",
        request_id="req-canvas-auto",
        user_id="u_test",
    )
    publish_canvas_event(canvas_id, "commit", {"foo": "bar"}, "u_test", ctx)
    
    # 2. Connect SSE (should pass 404/403 check if registered)
    # Implicitly uses mock_req_ctx with t_test
    with client.stream("GET", f"/sse/canvas/{canvas_id}") as response:
        assert response.status_code == 200
        first = next(response.iter_lines())
        assert first.startswith("id: ")

def test_sse_tenant_mismatch():
    async def bad_sse_ctx(*args, **kwargs):
        return RequestContext(tenant_id="t_other", env="dev", mode="saas", project_id="p_chat", request_id="req-canvas-bad", user_id="u_test")
    
    app.dependency_overrides[_sse_context] = bad_sse_ctx
    
    response = client.get("/sse/canvas/canvas-1")
    assert response.status_code == 403
    response.read()
    payload = response.json()
    assert payload["error"]["code"] == "auth.tenant_mismatch"
    assert payload["error"]["http_status"] == 403
    
    # Restore override
    app.dependency_overrides[_sse_context] = mock_sse_context


def test_sse_canvas_invalid_ticket():
    with patch.dict(os.environ, {"ENGINES_TICKET_SECRET": "ticket-secret"}):
        response = client.get("/sse/canvas/canvas-invalid?ticket=bad")
    assert response.status_code == 401
    response.read()
    payload = response.json()
    assert payload["error"]["code"] == "auth.ticket_invalid"
    assert payload["error"]["http_status"] == 401


def test_sse_canvas_invalid_cursor():
    canvas_id = "canvas-invalid-cursor"
    ctx = RequestContext(
        tenant_id="t_test",
        env="dev",
        project_id="p_chat",
        request_id="req-canvas-invalid",
        user_id="u_test",
    )
    publish_canvas_event(canvas_id, "commit", {"foo": "bar"}, "u_test", ctx)

    headers = {
        "Authorization": "Bearer token",  # actual value not used because override
        "X-Tenant-Id": "t_test",
        "X-Mode": "saas",
        "X-Project-Id": "p_chat",
        "X-Request-Id": "req-canvas-invalid",
        "X-Surface-Id": "surf",
        "X-App-Id": "app",
        "Last-Event-ID": "invalid-cursor",
    }

    response = client.get(f"/sse/canvas/{canvas_id}", headers=headers)
    assert response.status_code == 410
    response.read()
    payload = response.json()
    assert payload["error"]["code"] == "canvas.cursor_invalid"
    assert payload["error"]["http_status"] == 410
