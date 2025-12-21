"""Tests for Session Memory Engine."""
import os
from unittest import mock
from uuid import uuid4
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.common.identity import RequestContext
from engines.identity.jwt_service import default_jwt_service
from engines.nexus.memory.service import SessionMemoryService, _GLOBAL_MEMORY
from engines.nexus.memory.models import SessionTurn
from engines.nexus.memory.routes import router

os.environ.setdefault("AUTH_JWT_SIGNING", "phase2-secret")


def _auth_token(tenant_id: str = "t_demo", user_id: str = "u_demo") -> str:
    svc = default_jwt_service()
    claims = {
        "sub": user_id,
        "email": f"{user_id}@example.com",
        "tenant_ids": [tenant_id],
        "default_tenant_id": tenant_id,
        "role_map": {tenant_id: "member"},
    }
    return svc.issue_token(claims)


def _auth_headers(tenant_id: str = "t_demo", request_tenant: str | None = None) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_auth_token(tenant_id=tenant_id)}",
        "X-Tenant-Id": request_tenant or tenant_id,
        "X-Env": "dev",
    }

@pytest.fixture(autouse=True)
def clean_memory():
    _GLOBAL_MEMORY.clear()
    yield
    _GLOBAL_MEMORY.clear()

def test_memory_isolation():
    """Verify different tenants cannot see each other's sessions."""
    service = SessionMemoryService()
    
    ctx1 = RequestContext(tenant_id="t_1", env="dev", user_id="u1")
    ctx2 = RequestContext(tenant_id="t_2", env="dev", user_id="u2")
    
    sid = "sess_abc"
    t1 = SessionTurn(session_id=sid, role="user", content="hello")
    service.add_turn(ctx1, sid, t1)
    
    # Context 1 should see it
    snap1 = service.get_session(ctx1, sid)
    assert len(snap1.turns) == 1
    assert snap1.turns[0].content == "hello"
    
    # Context 2 querying SAME session ID shaould get EMPTY (different key space)
    snap2 = service.get_session(ctx2, sid)
    assert len(snap2.turns) == 0


def test_routes_smoke():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    headers = {**_auth_headers(), "X-User-Id": "u_test"}
    sid = str(uuid4())
    
    # 1. Add Turn
    turn_data = {
        "session_id": sid,
        "role": "user",
        "content": "api test"
    }
    with mock.patch("engines.nexus.hardening.gate_chain.GateChain.run"):
        with mock.patch("engines.nexus.memory.service.default_event_logger"):
            resp = client.post(f"/nexus/memory/session/{sid}/turn", json=turn_data, headers=headers)
        
    assert resp.status_code == 200
    saved = resp.json()
    assert saved["content"] == "api test"
    
    # 2. Get Session
    with mock.patch("engines.nexus.memory.service.default_event_logger"):
        resp = client.get(f"/nexus/memory/session/{sid}", headers=headers)
        
    assert resp.status_code == 200
    snap = resp.json()
    assert snap["session_id"] == sid
    assert len(snap["turns"]) == 1
    assert snap["turns"][0]["content"] == "api test"


def test_memory_requires_auth():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    headers = {"X-Tenant-Id": "t_demo", "X-Env": "dev"}
    sid = str(uuid4())
    turn_data = {"session_id": sid, "role": "user", "content": "missing auth"}
    resp = client.post(f"/nexus/memory/session/{sid}/turn", json=turn_data, headers=headers)
    assert resp.status_code == 401


def test_memory_reject_cross_tenant():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    sid = str(uuid4())
    turn_data = {"session_id": sid, "role": "user", "content": "cross tenant"}
    headers = {**_auth_headers(tenant_id="t_beta", request_tenant="t_demo"), "Content-Type": "application/json"}
    with mock.patch("engines.nexus.memory.service.default_event_logger"):
        resp = client.post(f"/nexus/memory/session/{sid}/turn", json=turn_data, headers=headers)
    assert resp.status_code == 403
