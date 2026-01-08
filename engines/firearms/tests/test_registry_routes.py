import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.common.identity import RequestContext
from engines.firearms.registry_routes import router
from engines.firearms.service import get_firearms_service, FirearmsService
from engines.firearms.repository import InMemoryFirearmsRepository

# Setup App
app = FastAPI()
app.include_router(router)

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_service():
    repo = InMemoryFirearmsRepository()
    svc = FirearmsService(repo=repo)
    # Override dependency
    app.dependency_overrides[get_firearms_service] = lambda: svc
    return svc

def test_create_and_list_license_types(client, mock_service):
    # Mock Auth Headers
    headers = {
        "X-Tenant-Id": "t1",
        "X-Mode": "saas",
        "X-User-Id": "u1",
        "X-User-Role": "admin" # Required for creation
    }
    
    # 1. List (Empty)
    res = client.get("/registry/firearms/license-types", headers=headers)
    assert res.status_code == 200
    assert res.json() == []

    # 2. Create
    payload = {
        "id": "lic_db_write",
        "name": "Database Write"
    }
    res = client.post("/registry/firearms/license-types", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "lic_db_write"
    assert data["name"] == "Database Write"

    # 3. List (populated)
    res = client.get("/registry/firearms/license-types", headers=headers)
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["id"] == "lic_db_write"

def test_tenant_isolation(client, mock_service):
    # Create in T1
    h1 = {"X-Tenant-Id": "t1", "X-Mode": "saas", "X-User-Id": "u1", "X-User-Role": "admin"}
    client.post("/registry/firearms/license-types", json={"name": "T1 Lic"}, headers=h1)

    # Check T2
    h2 = {"X-Tenant-Id": "t2", "X-Mode": "saas", "X-User-Id": "u2", "X-User-Role": "admin"}
    res = client.get("/registry/firearms/license-types", headers=h2)
    assert res.status_code == 200
    assert res.json() == [] # Should be empty

def test_permissions(client, mock_service):
    # Try to create as 'member' (not admin)
    headers = {
        "X-Tenant-Id": "t1",
        "X-Mode": "saas",
        "X-User-Id": "u1",
        "X-User-Role": "member"
    }
    res = client.post("/registry/firearms/license-types", json={"name": "Fail"}, headers=headers)
    assert res.status_code == 403 # Forbidden
