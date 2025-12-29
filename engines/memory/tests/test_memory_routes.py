from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.state import set_identity_repo
from engines.identity.models import Tenant, User, TenantMembership, TenantKeyConfig
from engines.identity.key_service import KeyConfigService
from engines.identity.routes_keys import set_key_service
from engines.common.keys import TenantKeySelector
from engines.identity.jwt_service import JwtService
from engines.memory.service import set_memory_service, MemoryService
from engines.memory.repository import FileMemoryRepository
from engines.memory.routes import router as memory_router
import pytest


def _setup(tmp_path):
    repo = InMemoryIdentityRepository()
    set_identity_repo(repo)
    os.environ["APP_ENV"] = "dev"
    os.environ["AUTH_JWT_SIGNING"] = "secret"
    repo.set_key_config(
        TenantKeyConfig(
            tenant_id="system",
            env="prod",
            slot="auth_jwt_signing",
            provider="system",
            secret_name="AUTH_JWT_SIGNING",
        )
    )
    set_key_service(KeyConfigService(repo=repo))
    tenant = Tenant(id="t_demo", name="Demo")
    user = User(email="memory@example.com")
    repo.create_tenant(tenant)
    repo.create_user(user)
    repo.create_membership(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    selector = TenantKeySelector(repo)
    jwt = JwtService(selector)
    token = jwt.issue_token(
        {
            "sub": user.id,
            "email": user.email,
            "tenant_ids": [tenant.id],
            "default_tenant_id": tenant.id,
            "role_map": {tenant.id: "owner"},
        }
    )
    storage_dir = tmp_path / "memory"
    set_memory_service(
        MemoryService(repo=FileMemoryRepository(base_dir=str(storage_dir)))
    )
    headers = {
        "X-Tenant-Id": tenant.id,
        "X-Mode": "saas",
        "X-Project-Id": "proj_memory",
        "X-Surface-Id": "surface_memory",
        "X-App-Id": "app_memory",
        "Authorization": f"Bearer {token}",
    }
    return tenant, headers


def _test_client() -> TestClient:
    app = FastAPI()
    app.include_router(memory_router)
    return TestClient(app)


def test_session_memory_append_and_read(tmp_path):
    tenant, headers = _setup(tmp_path)
    client = _test_client()
    payload = {"role": "user", "content": "hi"}
    resp = client.post("/memory/session/messages", params={"session_id": "s1"}, json=payload, headers=headers)
    assert resp.status_code == 200
    resp_get = client.get("/memory/session/messages", params={"session_id": "s1"}, headers=headers)
    assert resp_get.status_code == 200
    assert resp_get.json()["messages"][0]["content"] == "hi"


def test_blackboard_write_read_clear(tmp_path):
    tenant, headers = _setup(tmp_path)
    client = _test_client()
    board = {
        "tenant_id": tenant.id,
        "scope": "session",
        "key": "k1",
        "mode": "saas",
        "project_id": "proj_memory",
        "data": {"x": 1},
    }
    resp_put = client.put("/memory/blackboards/k1", json=board, headers=headers)
    assert resp_put.status_code == 200
    resp_get = client.get("/memory/blackboards/k1", headers=headers)
    assert resp_get.status_code == 200
    assert resp_get.json()["data"]["x"] == 1
    resp_del = client.delete("/memory/blackboards/k1", headers=headers)
    assert resp_del.status_code == 200
    resp_get2 = client.get("/memory/blackboards/k1", headers=headers)
    assert resp_get2.status_code == 200
    assert resp_get2.json() == {}


def test_memory_tenant_isolation(tmp_path):
    _, headers = _setup(tmp_path)
    client = _test_client()
    payload = {"role": "user", "content": "hi"}
    client.post("/memory/session/messages", params={"session_id": "s1"}, json=payload, headers=headers)
    other_headers = {
        "X-Tenant-Id": "t_other",
        "X-Mode": "saas",
        "X-Project-Id": "proj_memory",
        "Authorization": headers["Authorization"],
    }
    resp = client.get("/memory/session/messages", params={"session_id": "s1"}, headers=other_headers)
    assert resp.status_code in {400, 403}


def test_firestore_memory_repo_guarded():
    if not os.getenv("MEMORY_FIRESTORE_TEST"):
        pytest.skip("MEMORY_FIRESTORE_TEST not set")
    pytest.skip("Firestore tests are not configured in this environment")
