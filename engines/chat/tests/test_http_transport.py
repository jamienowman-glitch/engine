import os

from fastapi.testclient import TestClient

from engines.chat import pipeline
from engines.chat.service import llm_client
from engines.chat.service.server import create_app
from engines.identity.jwt_service import default_jwt_service


def setup_module(_module):
    os.environ.setdefault("AUTH_JWT_SIGNING", "chat-secret")
    os.environ.setdefault("APP_ENV", "dev")


def _auth_token(tenant_id: str = "t_chat", user_id: str = "u1"):
    svc = default_jwt_service()
    claims = {
        "sub": user_id,
        "email": f"{user_id}@example.com",
        "tenant_ids": [tenant_id],
        "default_tenant_id": tenant_id,
        "role_map": {tenant_id: "member"},
    }
    return svc.issue_token(claims)


def _auth_headers(
    tenant_id: str = "t_chat",
    env: str = "dev",
    request_id: str = "req-123",
    user_id: str = "u1",
):
    token = _auth_token(tenant_id=tenant_id, user_id=user_id)
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": tenant_id,
        "X-Env": env,
        "X-Request-Id": request_id,
        "X-User-Id": user_id,
    }


class StubBackend:
    def write_snippet(self, kind, doc, tags=None):
        return {}

    def write_event(self, event):
        return {}

    def get_latest_plan(self, *args, **kwargs):
        return None


def test_http_thread_and_messages_authenticated(monkeypatch):
    recorded_events: list = []
    monkeypatch.setattr(llm_client, "stream_chat", lambda **kwargs: iter(["hi there"]))
    monkeypatch.setattr(pipeline, "llm_client", llm_client)
    backend = StubBackend()
    monkeypatch.setattr(pipeline, "get_backend", lambda: backend)
    monkeypatch.setattr(pipeline, "log_event", lambda event: recorded_events.append(event))

    client = TestClient(create_app())
    headers = _auth_headers(request_id="req-123")
    resp = client.post("/chat/threads", json=[{"id": "u1"}], headers=headers)
    assert resp.status_code == 200
    thread_id = resp.json()["id"]

    resp = client.post(
        f"/chat/threads/{thread_id}/messages",
        json={"sender": {"id": "u1"}, "text": "hello"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert recorded_events, "expected dataset event"
    event = recorded_events[-1]
    assert event.tenantId == headers["X-Tenant-Id"]
    assert event.env == headers["X-Env"]
    assert event.requestId == headers["X-Request-Id"]
    assert event.traceId == headers["X-Request-Id"]


def test_chat_http_missing_auth_rejected():
    client = TestClient(create_app())
    headers = {
        "X-Tenant-Id": "t_chat",
        "X-Env": "dev",
        "X-Request-Id": "req-no-auth",
        "X-User-Id": "u1",
    }
    resp = client.post("/chat/threads", json={"participants": []}, headers=headers)
    assert resp.status_code == 401


def test_chat_http_cross_tenant_rejected():
    client = TestClient(create_app())
    headers = _auth_headers()
    headers["X-Tenant-Id"] = "t_other"
    resp = client.post("/chat/threads", json={"participants": []}, headers=headers)
    assert resp.status_code == 403
