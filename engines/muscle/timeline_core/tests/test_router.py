
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime, timezone

from engines.timeline_core.router import router, get_service
from engines.timeline_core.service import TimelineService
from engines.timeline_core.models import Task
from engines.common.identity import get_request_context, RequestContext

app = FastAPI()
app.include_router(router)

@pytest.fixture
def client():
    # Override dependency to ensure fresh service for each test?
    # Or just clear the global service. 
    # For simplicity, we'll swap the service singleton via dependency override.
    service = TimelineService()
    app.dependency_overrides[get_service] = lambda: service
    return TestClient(app)

@pytest.fixture
def headers():
    return {
        "x-tenant-id": "t_tenant_a",
        "x-env": "dev",
        "x-user-id": "user1"
    }

def test_create_and_list(client, headers):
    t = {
        "tenant_id": "t_tenant_a", # Will be overwritten by router from headers, but validated by Pydantic
        "env": "dev",
        "request_id": "req1",
        "title": "My Task",
        "start_ts": datetime.now(timezone.utc).isoformat()
    }
    
    # Create
    resp = client.post("/timeline/tasks", json=t, headers=headers)
    assert resp.status_code == 200
    tid = resp.json()
    assert tid
    
    # List
    resp = client.get("/timeline/tasks", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == tid
    assert data[0]["title"] == "My Task"

def test_gantt(client, headers):
    # Create task
    t = {
        "tenant_id": "t_tenant_a",
        "env": "dev",
        "request_id": "req1",
        "title": "My Task",
        "start_ts": datetime.now(timezone.utc).isoformat()
    }
    client.post("/timeline/tasks", json=t, headers=headers)
    
    # View
    resp = client.get("/timeline/view/gantt", headers=headers)
    assert resp.status_code == 200
    view = resp.json()
    assert len(view["unscoped_items"]) == 1
    assert view["unscoped_items"][0]["label"] == "My Task"

def test_isolation(client):
    h1 = {"x-tenant-id": "t_t1", "x-env": "dev", "x-user-id": "u1"}
    h2 = {"x-tenant-id": "t_t2", "x-env": "dev", "x-user-id": "u2"}
    
    t = {
        "tenant_id": "t_t1", # dummy
        "env": "dev",
        "request_id": "req",
        "title": "T1 Task",
        "start_ts": datetime.now(timezone.utc).isoformat()
    }
    
    client.post("/timeline/tasks", json=t, headers=h1)
    
    # T2 should see empty
    resp = client.get("/timeline/tasks", headers=h2)
    assert resp.status_code == 200
    assert len(resp.json()) == 0
