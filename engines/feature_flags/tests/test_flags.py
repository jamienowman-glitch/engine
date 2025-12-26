import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from engines.feature_flags.routes import router as flags_router
from engines.feature_flags.models import FeatureFlags
from engines.feature_flags.repository import (
    FeatureFlagRepository,
    GLOBAL_TENANT_ID,
    feature_flag_repo,
)
from engines.identity.routes_auth import router as auth_router
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context

# Mock Auth/Context Overrides
async def mock_request_context():
    return RequestContext(tenant_id="t_test",
        env="dev",
        user_id="u_test",
        membership_role="member" # Default member
    )

async def mock_auth_context():
    return AuthContext(
        user_id="u_test",
        email="test@example.com",
        tenant_ids=["t_test"],
        default_tenant_id="t_test",
        role_map={"t_test": "member"}
    )

# App Setup
app = FastAPI()
app.include_router(flags_router)

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_flags():
    feature_flag_repo._store.clear()
    app.dependency_overrides = {}

class _FakeFirestoreSnapshot:
    def __init__(self, data, exists: bool):
        self._data = data
        self.exists = exists

    def to_dict(self):
        return self._data


class _FakeFirestoreDoc:
    def __init__(self):
        self._data = None
        self.exists = False

    def set(self, payload):
        self._data = payload
        self.exists = True

    def get(self):
        return _FakeFirestoreSnapshot(self._data, self.exists)

    def delete(self):
        self._data = None
        self.exists = False


class _FakeFirestoreCollection:
    def __init__(self):
        self._docs = {}

    def document(self, doc_id):
        doc = self._docs.get(doc_id)
        if doc is None:
            doc = _FakeFirestoreDoc()
            self._docs[doc_id] = doc
        return doc


class _FakeFirestoreClient:
    def __init__(self):
        self._collections = {}

    def collection(self, name):
        collection = self._collections.get(name)
        if collection is None:
            collection = _FakeFirestoreCollection()
            self._collections[name] = collection
        return collection

def test_get_defaults():
    app.dependency_overrides[get_request_context] = mock_request_context
    app.dependency_overrides[get_auth_context] = mock_auth_context

    response = client.get("/feature-flags")
    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == "t_test"
    assert data["ws_enabled"] is False

def test_update_flags_owner():
    # Override as owner
    async def mock_owner_ctx():
        return RequestContext(tenant_id="t_test",
            env="dev",
            user_id="u_owner",
            membership_role="owner"
        )
    async def mock_owner_auth():
        return AuthContext(
            user_id="u_owner",
            email="owner@example.com",
            tenant_ids=["t_test"],
            default_tenant_id="t_test",
            role_map={"t_test": "owner"}
        )
    
    app.dependency_overrides[get_request_context] = mock_owner_ctx
    app.dependency_overrides[get_auth_context] = mock_owner_auth

    global_entry = FeatureFlags(
        tenant_id=GLOBAL_TENANT_ID,
        env="dev",
        ws_enabled=False,
        replay_mode="off",
    )
    feature_flag_repo.set_flags(global_entry)

    payload = {
        "tenant_id": "t_test",
        "env": "dev",
        "ws_enabled": True,
        "visibility_mode": "team"
    }
    response = client.put("/feature-flags", json=payload)
    assert response.status_code == 200
    assert response.json()["ws_enabled"] is True

    # Verify get gets updated
    response = client.get("/feature-flags")
    assert response.json()["ws_enabled"] is True

    assert feature_flag_repo.get_global_flags("dev").ws_enabled is False

def test_update_flags_member_forbidden():
    # Default is member
    app.dependency_overrides[get_request_context] = mock_request_context
    app.dependency_overrides[get_auth_context] = mock_auth_context

    payload = {
        "tenant_id": "t_test",
        "env": "dev",
        "ws_enabled": True
    }
    response = client.put("/feature-flags", json=payload)
    assert response.status_code == 403


def test_global_flag_fallback():
    app.dependency_overrides[get_request_context] = mock_request_context
    app.dependency_overrides[get_auth_context] = mock_auth_context

    global_entry = FeatureFlags(
        tenant_id=GLOBAL_TENANT_ID,
        env="dev",
        ws_enabled=True,
        replay_mode="stream",
    )
    feature_flag_repo.set_flags(global_entry)

    response = client.get("/feature-flags")
    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == "t_test"
    assert data["ws_enabled"] is True
    assert data["replay_mode"] == "stream"


def test_firestore_repository_persists():
    fake_client = _FakeFirestoreClient()
    repo = FeatureFlagRepository(backend="firestore", firestore_client=fake_client)
    flags = FeatureFlags(tenant_id="t_test", env="dev", ws_enabled=True)
    repo.set_flags(flags)

    doc = fake_client.collection("feature_flags").document("t_test__dev")
    assert doc._data is not None
    assert doc._data["ws_enabled"] is True
