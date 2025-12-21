from __future__ import annotations

import os

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.state import set_identity_repo
from engines.identity.models import Tenant, User, TenantMembership, TenantKeyConfig
from engines.identity.key_service import KeyConfigService
from engines.identity.routes_keys import set_key_service
from engines.common.keys import TenantKeySelector
from engines.identity.jwt_service import JwtService
from engines.memory.service import set_memory_service, MemoryService
from engines.memory.repository import InMemoryMemoryRepository, FirestoreMemoryRepository
import pytest


def _setup():
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
    headers = {"X-Tenant-Id": tenant.id, "X-Env": "dev", "Authorization": f"Bearer {token}"}
    set_memory_service(MemoryService(repo=InMemoryMemoryRepository()))
    return tenant, headers


def test_session_memory_append_and_read():
    tenant, headers = _setup()
    client = TestClient(create_app())
    payload = {"role": "user", "content": "hi"}
    resp = client.post("/memory/session/messages", params={"session_id": "s1"}, json=payload, headers=headers)
    assert resp.status_code == 200
    resp_get = client.get("/memory/session/messages", params={"session_id": "s1"}, headers=headers)
    assert resp_get.status_code == 200
    assert resp_get.json()["messages"][0]["content"] == "hi"


def test_blackboard_write_read_clear():
    tenant, headers = _setup()
    client = TestClient(create_app())
    board = {"tenant_id": tenant.id, "env": "dev", "scope": "session", "key": "k1", "data": {"x": 1}}
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


def test_memory_tenant_isolation():
    tenant, headers = _setup()
    client = TestClient(create_app())
    payload = {"role": "user", "content": "hi"}
    client.post("/memory/session/messages", params={"session_id": "s1"}, json=payload, headers=headers)
    other_headers = {"X-Tenant-Id": "t_other", "X-Env": "dev", "Authorization": headers["Authorization"]}
    resp = client.get("/memory/session/messages", params={"session_id": "s1"}, headers=other_headers)
    assert resp.status_code in {400, 403}


def test_firestore_memory_repo_guarded():
    if not os.getenv("MEMORY_FIRESTORE_TEST"):
        pytest.skip("MEMORY_FIRESTORE_TEST not set")
    try:
        FirestoreMemoryRepository()
    except Exception as exc:
        pytest.skip(f"Firestore not available: {exc}")
