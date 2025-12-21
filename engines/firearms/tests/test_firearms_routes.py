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
from engines.firearms.service import FirearmsService
from engines.firearms.repository import InMemoryFirearmsRepository, FirestoreFirearmsRepository
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
    user = User(email="firearms@example.com")
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
    return tenant, headers


def test_issue_list_revoke_and_gate():
    tenant, headers = _setup()
    client = TestClient(create_app())
    payload = {
        "tenant_id": tenant.id,
        "env": "dev",
        "subject_type": "agent",
        "subject_id": "agent123",
        "scope": "tool_use",
        "level": "medium",
    }
    resp_issue = client.post("/firearms/licences", json=payload, headers=headers)
    assert resp_issue.status_code == 200
    licence_id = resp_issue.json()["id"]
    # check gate allowed
    resp_gate = client.post("/firearms/licences/dangerous-demo/agent/agent123", headers=headers)
    assert resp_gate.status_code == 200
    # revoke
    resp_revoke = client.patch(f"/firearms/licences/{licence_id}", headers=headers)
    assert resp_revoke.status_code == 200
    # now gate should fail
    resp_gate2 = client.post("/firearms/licences/dangerous-demo/agent/agent123", headers=headers)
    assert resp_gate2.status_code == 403


def test_firearms_tenant_isolation():
    tenant, headers = _setup()
    client = TestClient(create_app())
    payload = {
        "tenant_id": tenant.id,
        "env": "dev",
        "subject_type": "agent",
        "subject_id": "agent123",
        "level": "low",
    }
    client.post("/firearms/licences", json=payload, headers=headers)
    other_headers = {"X-Tenant-Id": "t_other", "X-Env": "dev", "Authorization": headers["Authorization"]}
    resp = client.get("/firearms/licences", headers=other_headers)
    assert resp.status_code in {400, 403}


def test_firestore_repo_instantiation_guarded():
    if not os.getenv("FIREARMS_FIRESTORE_TEST"):
        pytest.skip("FIREARMS_FIRESTORE_TEST not set")
    try:
        FirestoreFirearmsRepository()
    except Exception as exc:
        pytest.skip(f"Firestore not available: {exc}")
