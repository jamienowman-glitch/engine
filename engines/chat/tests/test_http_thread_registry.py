import pytest
from fastapi.testclient import TestClient
from engines.chat.service.server import create_app
from engines.realtime.isolation import registry, InMemoryResourceRegistry

@pytest.fixture
def clean_registry():
    # Ensure we start with a clean in-memory registry
    if hasattr(registry, "clear"):
        registry.clear()
    elif isinstance(registry, InMemoryResourceRegistry):
        registry._threads.clear()
        registry._canvases.clear()
    return registry

def test_thread_auto_registered_on_creation(clean_registry):
    """
    L1-T1 Verification:
    Assert registry contains the thread after POST /chat/threads.
    """
    app = create_app()
    client = TestClient(app)
    
    tenant_id = "t_test-tenant-1"
    headers = {
        "x-tenant-id": tenant_id,
        "x-user-id": "user-1",
        "x-env": "dev"
    }
    
    # Mock Auth
    from engines.identity.auth import get_auth_context, AuthContext

    def mock_get_auth_context():
        return AuthContext(
            user_id="user-1",
            email="test@example.com",
            tenant_ids=["t_test-tenant-1"],
            default_tenant_id="t_test-tenant-1",
            role_map={"t_test-tenant-1": "owner"},
            provider="test",
            claims={}
        )

    app.dependency_overrides[get_auth_context] = mock_get_auth_context

    # 1. Create thread via HTTP
    resp = client.post("/chat/threads", json=[], headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    thread_id = data["id"]
    
    # 2. Verify registry has it
    owner = clean_registry.get_thread_tenant(thread_id)
    assert owner == tenant_id, f"Thread {thread_id} not registered to {tenant_id}"
