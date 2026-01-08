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

from engines.identity.auth import get_auth_context
from engines.identity.jwt_service import AuthContext
from fastapi import Header

@pytest.fixture
def mock_service():
    repo = InMemoryFirearmsRepository()
    svc = FirearmsService(repo=repo)
    # Override service dependency
    app.dependency_overrides[get_firearms_service] = lambda: svc
    
    # Override auth dependency
    def fake_auth_context(
        x_user_id: str = Header("u1"),
        x_tenant_id: str = Header("t1"),
        x_membership_role: str = Header(None)
    ):
        return AuthContext(
            user_id=x_user_id,
            email="test@example.com",
            tenant_ids=[x_tenant_id],
            default_tenant_id=x_tenant_id,
            role_map={x_tenant_id: x_membership_role} if x_membership_role else {}
        )
    
    app.dependency_overrides[get_auth_context] = fake_auth_context
    yield svc
    app.dependency_overrides = {}

def test_create_and_list_license_types(client, mock_service):
    # Mock Auth Headers
    headers = {
        "X-Tenant-Id": "t_test",
        "X-Mode": "saas",
        "X-User-Id": "u1",
        "X-Membership-Role": "admin", # Required for creation
        "X-Project-Id": "p_test",
        "X-App-Id": "app_test",
        "X-Surface-Id": "surface_test"
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
    h1 = {"X-Tenant-Id": "t_test", "X-Mode": "saas", "X-User-Id": "u1", "X-Membership-Role": "admin", "X-Project-Id": "p_test", "X-App-Id": "app_test", "X-Surface-Id": "surface_test"}
    client.post("/registry/firearms/license-types", json={"name": "T1 Lic"}, headers=h1)

    # Check T2
    h2 = {"X-Tenant-Id": "t_other", "X-Mode": "saas", "X-User-Id": "u2", "X-Membership-Role": "admin", "X-Project-Id": "p_test", "X-App-Id": "app_test", "X-Surface-Id": "surface_test"}
    res = client.get("/registry/firearms/license-types", headers=h2)
    assert res.status_code == 200
    assert res.json() == [] # Should be empty

def test_permissions(client, mock_service):
    # Try to create as 'member' (not admin)
    headers = {
        "X-Tenant-Id": "t_test",
        "X-Mode": "saas",
        "X-User-Id": "u1",
        "X-Membership-Role": "member",
        "X-Project-Id": "p_test",
        "X-App-Id": "app_test",
        "X-Surface-Id": "surface_test"
    }
    res = client.post("/registry/firearms/license-types", json={"name": "Fail"}, headers=headers)
    assert res.status_code == 403 # Forbidden

def test_inspect_policy(client, mock_service):
    # 1. Setup binding
    from engines.firearms.models import FirearmBinding
    from engines.common.identity import RequestContext
    
    # We need to manually set up the binding in the repo
    # The client/app doesn't expose a direct binding creation endpoint in this router (it's internal/admin usually)
    # So we use the mock service directly
    repo = mock_service.repo
    ctx = RequestContext(tenant_id="t_test", env="dev", mode="saas")
    repo.create_binding(ctx, FirearmBinding(
        action_name="tool.danger.exec",
        firearm_id="lic_danger"
    ))
    
    headers = {
        "X-Tenant-Id": "t_test", 
        "X-Mode": "saas", 
        "X-User-Id": "u1", 
        "X-Project-Id": "p_test",
        "X-App-Id": "app_test",
        "X-Surface-Id": "surface_test"
    }
    
    # 2. Inspect Unbound (Safe)
    res = client.get("/registry/firearms/inspect?tool_id=tool&scope_name=safe", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["requires_firearms"] is False
    assert data["tool_id"] == "tool"
    assert data["scope_name"] == "safe"
    
    # 3. Inspect Bound (Unsafe)
    res = client.get("/registry/firearms/inspect?tool_id=tool&scope_name=danger.exec", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["requires_firearms"] is True
    assert data["details"]["firearm_id"] == "lic_danger"
    assert data["details"]["strategy_lock_required"] is True
