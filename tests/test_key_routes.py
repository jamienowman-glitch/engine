from __future__ import annotations

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.common.identity import RequestContext
from engines.identity.key_service import KeyConfigService
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.routes_keys import set_key_service
from engines.common.secrets import SecretManagerClient
from engines.identity.models import Surface, App
from engines.identity.auth import AuthContext, get_auth_context

class FakeSecretManager(SecretManagerClient):
    def __init__(self):
        super().__init__(client=self)
        self.storage = {}

    def access_secret(self, secret_id: str) -> str:
        return self.storage[secret_id]

    def create_or_update_secret(self, secret_id: str, value: str) -> str:
        self.storage[secret_id] = value
        return secret_id

def mock_auth_context():
    return AuthContext(
        user_id="u_admin",
        email="admin@example.com",
        default_tenant_id="t_demo",
        tenant_ids=["t_demo"],
        role_map={"t_demo": "owner"}
    )

def _client():
    repo = InMemoryIdentityRepository()
    # Pre-seed surface and app for identity checks
    repo.create_surface(Surface(id="chat", tenant_id="t_demo", name="Chat", slug="chat"))
    repo.create_app(App(id="default", tenant_id="t_demo", name="Default App", slug="default"))

    secrets = FakeSecretManager()
    set_key_service(KeyConfigService(repo=repo, secrets=secrets))
    app = create_app()
    app.dependency_overrides[get_auth_context] = mock_auth_context
    return TestClient(app), repo, secrets


def test_key_slot_create_and_get():
    client, repo, secrets = _client()
    headers = {
        "X-Tenant-Id": "t_demo",
        "X-Mode": "saas",
        "X-Project-Id": "p_demo",
        "X-Surface-Id": "chat",
        "X-App-Id": "default"
    }
    payload = {
        "slot": "llm_primary",
        "env": "dev",
        "provider": "openai",
        "secret_value": "abc123",
        "metadata": {"region": "us"},
    }
    resp = client.post("/tenants/t_demo/keys", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["slot"] == "llm_primary"
    assert "secret_value" not in data
    # secret stored
    assert secrets.storage

    # list returns config without secret
    resp = client.get("/tenants/t_demo/keys", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert items and items[0]["secret_name"]

    # get specific slot
    resp = client.get("/tenants/t_demo/keys/llm_primary", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["provider"] == "openai"


def test_key_slot_mismatch_rejected():
    client, _, _ = _client()
    headers = {
        "X-Tenant-Id": "t_demo",
        "X-Mode": "saas",
        "X-Project-Id": "p_demo",
        "X-Surface-Id": "chat",
        "X-App-Id": "default"
    }
    payload = {
        "slot": "llm_primary",
        "env": "dev",
        "provider": "openai",
        "secret_value": "abc123",
    }
    resp = client.put("/tenants/t_demo/keys/other_slot", json=payload, headers=headers)
    assert resp.status_code == 400
