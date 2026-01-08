import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from engines.common.identity import RequestContext
from engines.workbench.routes import router
from engines.workbench.store import VersionedStore
from engines.workbench.publisher import PublisherService, get_publisher_service
from engines.storage.routing_service import TabularStoreService

# Mock Dependencies
app = FastAPI()
app.include_router(router)

@pytest.fixture
def client():
    return TestClient(app)

# Mock Store to avoid routing errors in tests
class MockVersionedStore:
    def __init__(self):
        self._drafts = {}
        self._versions = {}
    
    def put_draft(self, ctx, key, data):
        data["version"] = "draft"
        self._drafts[key] = MockItem(key, "draft", data)
    
    def get_draft(self, ctx, key):
        return self._drafts.get(key)
    
    def publish(self, ctx, key, version):
        draft = self._drafts.get(key)
        self._versions[(key, version)] = MockItem(key, version, draft.data)
        
    def get_version(self, ctx, key, version):
        return self._versions.get((key, version))

class MockItem:
    def __init__(self, key, version, data):
        self.key = key
        self.version = version
        self.data = data

@pytest.fixture(autouse=True)
def mock_store(monkeypatch):
    store = MockVersionedStore()
    from engines.workbench import routes
    monkeypatch.setattr(routes, "_store", store)
    return store

@pytest.fixture(autouse=True)
def mock_publisher():
    svc = MagicMock(spec=PublisherService)
    app.dependency_overrides[get_publisher_service] = lambda: svc
    return svc

def test_draft_save_load(client):
    headers = {"X-Tenant-Id": "t1", "X-Mode": "saas", "X-User-Id": "u1", "X-User-Role": "admin"}
    payload = {
        "name": "my_tool",
        "version": "1.0.0",
        "scopes": []
    }
    
    # Save
    res = client.put("/workbench/drafts/my_tool", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    
    # Load
    res = client.get("/workbench/drafts/my_tool", headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["name"] == "my_tool"

def test_publish(client, mock_publisher):
    headers = {"X-Tenant-Id": "t1", "X-Mode": "saas", "X-User-Id": "u1", "X-User-Role": "admin"}
    
    # Setup Draft
    client.put("/workbench/drafts/my_tool", json={
        "name": "my_tool",
        "version": "1.0.0",
        "scopes": [
            {"scope_name": "read", "requires_firearms": True, "required_license_types": ["lic_1"]}
        ]
    }, headers=headers)
    
    # Publish
    res = client.post("/workbench/publish", json={"tool_id": "my_tool"}, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["portable_package"]["package_id"] == "my_tool"
    
    # Publisher called?
    assert mock_publisher.publish.called
    # Check overlays logic
    args, _ = mock_publisher.publish.call_args
    # args[0] = ctx, args[1] = pkg, args[2] = overlay
    overlay = args[2]
    assert overlay.tools["my_tool"].scopes["read"].policy.firearms is True
