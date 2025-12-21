from __future__ import annotations

import os

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.identity.jwt_service import JwtService
from engines.identity.state import set_identity_repo, identity_repo
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.models import TenantKeyConfig, TenantMembership, Tenant, User
from engines.identity.key_service import KeyConfigService
from engines.identity.routes_keys import set_key_service


def _setup_repo_with_jwt_secret():
    repo = InMemoryIdentityRepository()
    set_identity_repo(repo)
    os.environ["APP_ENV"] = "dev"
    os.environ["AUTH_JWT_SIGNING"] = "super-secret"
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
    return repo


def test_signup_and_login_flow():
    repo = _setup_repo_with_jwt_secret()
    app = create_app()
    client = TestClient(app)

    # signup
    resp = client.post(
        "/auth/signup",
        json={"email": "a@example.com", "password": "pw123", "display_name": "A", "tenant_name": "Tenant A"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    assert token

    # login
    resp = client.post("/auth/login", json={"email": "a@example.com", "password": "pw123"})
    assert resp.status_code == 200
    token2 = resp.json()["access_token"]
    assert token2


def test_jwt_issue_and_roles():
    repo = _setup_repo_with_jwt_secret()
    tenant = Tenant(id="t_demo", name="Demo")
    user = User(email="b@example.com")
    repo.create_tenant(tenant)
    repo.create_user(user)
    repo.create_membership(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="admin"))

    from engines.common.keys import TenantKeySelector

    selector = TenantKeySelector(repo)
    jwt_svc = JwtService(selector)
    token = jwt_svc.issue_token(
        {
            "sub": user.id,
            "email": user.email,
            "tenant_ids": [tenant.id],
            "default_tenant_id": tenant.id,
            "role_map": {tenant.id: "admin"},
        }
    )
    decoded = jwt_svc.decode_token(token)
    assert tenant.id in decoded.tenant_ids
