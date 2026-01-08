import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.common.identity import RequestContext
from engines.kpi.registry_routes import router
from engines.kpi.service import get_kpi_service, KpiService
from engines.kpi.repository import InMemoryKpiRepository

# Setup App
app = FastAPI()
app.include_router(router)

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_service():
    repo = InMemoryKpiRepository()
    svc = KpiService(repo=repo)
    # Override dependency
    app.dependency_overrides[get_kpi_service] = lambda: svc
    return svc

def test_categories_crud(client, mock_service):
    headers = {"X-Tenant-Id": "t1", "X-Mode": "saas", "X-User-Id": "u1", "X-User-Role": "admin"}
    
    # List empty
    res = client.get("/registry/kpi/categories", headers=headers)
    assert res.status_code == 200
    assert res.json() == []

    # Create
    cat = {"id": "cat_perf", "name": "Performance", "tenant_id": "t1", "env": "live"}
    res = client.post("/registry/kpi/categories", json=cat, headers=headers)
    assert res.status_code == 200
    assert res.json()["name"] == "Performance"

    # List again
    res = client.get("/registry/kpi/categories", headers=headers)
    assert len(res.json()) == 1

def test_types_crud(client, mock_service):
    headers = {"X-Tenant-Id": "t1", "X-Mode": "saas", "X-User-Id": "u1", "X-User-Role": "admin"}
    
    # Create Type
    typ = {"id": "type_latency", "name": "Latency", "category_id": "cat_perf", "tenant_id": "t1", "env": "live"}
    res = client.post("/registry/kpi/types", json=typ, headers=headers)
    assert res.status_code == 200
    
    # List
    res = client.get("/registry/kpi/types", headers=headers)
    assert len(res.json()) == 1
    assert res.json()[0]["category_id"] == "cat_perf"

def test_tenant_isolation(client, mock_service):
    # Setup T1
    h1 = {"X-Tenant-Id": "t1", "X-Mode": "saas", "X-User-Id": "u1", "X-User-Role": "admin"}
    client.post("/registry/kpi/categories", json={"name": "T1 Cat"}, headers=h1)

    # Check T2
    h2 = {"X-Tenant-Id": "t2", "X-Mode": "saas", "X-User-Id": "u2", "X-User-Role": "admin"}
    res = client.get("/registry/kpi/categories", headers=h2)
    assert res.status_code == 200
    assert res.json() == []

def test_permissions(client, mock_service):
    # Member cannot create
    headers = {"X-Tenant-Id": "t1", "X-Mode": "saas", "X-User-Id": "u1", "X-User-Role": "member"}
    res = client.post("/registry/kpi/categories", json={"name": "Bad"}, headers=headers)
    assert res.status_code == 403
