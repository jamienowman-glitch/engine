from __future__ import annotations

import os

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.identity.state import set_identity_repo
from engines.identity.repository import InMemoryIdentityRepository
import pytest


def setup_function(_fn):
    # Fresh in-memory identity store per test
    set_identity_repo(InMemoryIdentityRepository())
    os.environ["AUTH_JWT_SIGNING"] = "dev-secret"


def _signup_and_login(client: TestClient, tenant_name: str = "Acme") -> tuple[str, str]:
    signup_resp = client.post(
        "/auth/signup",
        json={"email": "demo@example.com", "password": "pw1234", "tenant_name": tenant_name},
    )
    assert signup_resp.status_code == 200
    login_resp = client.post("/auth/login", json={"email": "demo@example.com", "password": "pw1234"})
    assert login_resp.status_code == 200
    body = login_resp.json()
    return body["access_token"], signup_resp.json()["tenant"]["id"]


def test_protected_keys_requires_membership():
    client = TestClient(create_app())
    token, tenant_id = _signup_and_login(client)

    # Allowed for member tenant
    resp = client.get(
        f"/tenants/{tenant_id}/keys",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-Id": tenant_id,
            "X-Mode": "saas",
            "X-Project-Id": "p_demo",
        },
    )
    assert resp.status_code == 200

    # Forbidden for other tenant
    resp2 = client.get(
        "/tenants/t_other/keys",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-Id": "t_other",
            "X-Mode": "saas",
            "X-Project-Id": "p_demo",
        },
    )
    assert resp2.status_code in {400, 403}


def test_missing_token_is_rejected():
    client = TestClient(create_app())
    resp = client.get(
        "/tenants/t_demo/keys",
        headers={"X-Tenant-Id": "t_demo", "X-Mode": "saas", "X-Project-Id": "p_demo"},
    )
    assert resp.status_code == 401


def test_firestore_repo_round_trip_skipped_without_env(monkeypatch):
    if not os.getenv("FIRESTORE_IDENTITY_TEST"):
        pytest.skip("FIRESTORE_IDENTITY_TEST not set")
    try:
        from engines.identity.repository import FirestoreIdentityRepository
        from engines.identity.models import User, Tenant, TenantMembership
    except Exception:
        pytest.skip("Firestore dependencies not available")
    # Require project env to avoid runtime_config failure
    if not (os.getenv("GCP_PROJECT") or os.getenv("GCP_PROJECT_ID")):
        pytest.skip("GCP_PROJECT not set for Firestore test")
    repo = FirestoreIdentityRepository()
    user = repo.create_user(User(email="fs@example.com"))
    tenant = repo.create_tenant(Tenant(id="t_fs_test", name="FS Test", created_by=user.id))
    membership = repo.create_membership(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    assert repo.get_user_by_email("fs@example.com") is not None
    assert repo.get_tenant(tenant.id) is not None
    assert repo.list_memberships_for_user(user.id)
    assert repo.list_tenants_for_user(user.id)[0].id == tenant.id
