"""Tests for Research Runs Engine."""
import os
from unittest import mock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.common.identity import RequestContext
from engines.identity.jwt_service import default_jwt_service
from engines.nexus.runs.service import ResearchRunService
from engines.nexus.runs.routes import router
from engines.dataset.events.schemas import DatasetEvent

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

# Mock Backend
class MockMemoryBackend:
    def __init__(self):
        self.events = []
    
    def query_events(self, tenant_id, env, limit=100):
        return [e for e in self.events if e.tenantId == tenant_id]

def test_list_runs_aggregation():
    """Verify events are aggregated into runs."""
    
    # Create some mock events
    e1 = DatasetEvent(
        tenantId="t_test", env="dev", surface="test", agentId="u1",
        input={"event_type": "pack_created", "asset_type": "pack"},
        output={"asset_id": "p1"},
        metadata={"trace_id": "trace_1"}
    )
    e2 = DatasetEvent(
        tenantId="t_test", env="dev", surface="test", agentId="u1",
        input={"event_type": "card_search", "asset_type": "search"},
        output={},
        metadata={"trace_id": "trace_1"}
    )
    # Different tenant
    e3 = DatasetEvent(
        tenantId="t_other", env="dev", surface="test", agentId="u2",
        input={"event_type": "pack_created"},
        output={},
        metadata={"trace_id": "trace_2"}
    )

    mock_backend = MockMemoryBackend()
    mock_backend.events = [e1, e2, e3]
    
    # Patch get_backend to return our mock
    with mock.patch("engines.nexus.runs.service.get_backend", return_value=mock_backend):
        service = ResearchRunService()
        ctx = RequestContext(tenant_id="t_test", env="dev", user_id="u1")
        
        runs = service.list_runs(ctx)
        
        assert len(runs) == 1
        run = runs[0]
        assert run.run_id == "trace_1"
        assert run.events_count == 2
        assert run.tenant_id == "t_test"


def test_routes_smoke():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    headers = {**_auth_headers(), "X-User-Id": "u_test"}
    
    with mock.patch("engines.nexus.runs.service.get_backend") as mock_get:
        mock_instance = MockMemoryBackend()
        mock_get.return_value = mock_instance
        
        resp = client.get("/nexus/runs", headers=headers)
    
    assert resp.status_code == 200
    assert resp.json() == []


def test_runs_require_auth():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    headers = {"X-Tenant-Id": "t_demo", "X-Env": "dev"}
    resp = client.get("/nexus/runs", headers=headers)
    assert resp.status_code == 401


def test_runs_reject_cross_tenant():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    headers = _auth_headers(tenant_id="t_beta", request_tenant="t_demo")
    with mock.patch("engines.nexus.runs.service.get_backend") as mock_get:
        mock_get.return_value = MockMemoryBackend()
        resp = client.get("/nexus/runs", headers=headers)
    assert resp.status_code == 403
