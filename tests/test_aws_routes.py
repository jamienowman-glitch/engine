from __future__ import annotations

import os

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.debug import aws_routes
from engines.identity.jwt_service import default_jwt_service
from engines.identity.models import Tenant, TenantMembership, User
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.state import set_identity_repo


def _setup_identity():
    os.environ["AUTH_JWT_SIGNING"] = "dev-secret"
    repo = InMemoryIdentityRepository()
    set_identity_repo(repo)
    tenant = repo.create_tenant(Tenant(id="t_demo", name="Demo"))
    user = repo.create_user(User(email="aws@example.com", password_hash="pw"))
    repo.create_membership(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    token = default_jwt_service().issue_token(
        {"sub": user.id, "email": user.email, "tenant_ids": [tenant.id], "default_tenant_id": tenant.id, "role_map": {tenant.id: "owner"}}
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": tenant.id,
        "X-Mode": "saas",
        "X-Project-Id": "p_demo",
    }
    return headers


def test_debug_aws_identity(monkeypatch):
    headers = _setup_identity()
    monkeypatch.setattr(
        aws_routes,
        "aws_healthcheck",
        lambda: {"ok": True, "identity": {"account_id": "123", "arn": "arn:aws:iam::123:user/demo", "region": "us-east-1"}},
    )
    client = TestClient(create_app())
    resp = client.get("/debug/aws-identity", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["identity"]["account_id"] == "123"


def test_debug_aws_billing_probe(monkeypatch):
    headers = _setup_identity()
    monkeypatch.setattr(
        aws_routes,
        "aws_billing_probe",
        lambda: {"ok": False, "error": "access_denied", "missing_permission": "ce:GetCostAndUsage"},
    )
    client = TestClient(create_app())
    resp = client.get("/debug/aws-billing-probe", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert body["missing_permission"] == "ce:GetCostAndUsage"
