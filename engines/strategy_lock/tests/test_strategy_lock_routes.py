from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.identity.passwords import hash_password
from engines.identity.state import set_identity_repo
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.models import User, TenantMembership
from engines.strategy_lock.repository import InMemoryStrategyLockRepository
from engines.strategy_lock.service import StrategyLockService, set_strategy_lock_service
from engines.strategy_lock.state import set_strategy_lock_repo


def setup_function(_fn):
    set_identity_repo(InMemoryIdentityRepository())
    repo = InMemoryStrategyLockRepository()
    set_strategy_lock_repo(repo)
    set_strategy_lock_service(StrategyLockService(repo))
    os.environ["AUTH_JWT_SIGNING"] = "dev-secret"


def _client():
    return TestClient(create_app())


def _signup_and_login(client: TestClient, email: str = "demo@example.com", tenant_name: str = "Acme") -> tuple[str, str]:
    signup_resp = client.post("/auth/signup", json={"email": email, "password": "pw1234", "tenant_name": tenant_name})
    assert signup_resp.status_code == 200
    login_resp = client.post("/auth/login", json={"email": email, "password": "pw1234"})
    assert login_resp.status_code == 200
    body = login_resp.json()
    return body["access_token"], signup_resp.json()["tenant"]["id"]


def test_create_and_approve_strategy_lock_flow():
    client = _client()
    token, tenant_id = _signup_and_login(client)
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Id": tenant_id, "X-Env": "dev"}
    payload = {
        "surface": "squared",
        "scope": "budget",
        "title": "Budget Lock",
        "description": "Keep budgets pinned",
        "constraints": {"max_monthly": 1000},
        "allowed_actions": ["budget:update"],
    }
    create_resp = client.post("/strategy-locks", json=payload, headers=headers)
    assert create_resp.status_code == 200
    lock_id = create_resp.json()["id"]

    approve_resp = client.post(f"/strategy-locks/{lock_id}/approve", headers=headers)
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"

    get_resp = client.get(f"/strategy-locks/{lock_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "approved"


def test_role_enforcement_on_approve():
    client = _client()
    owner_token, tenant_id = _signup_and_login(client, email="owner@example.com", tenant_name="RoleTest")
    headers_owner = {"Authorization": f"Bearer {owner_token}", "X-Tenant-Id": tenant_id, "X-Env": "dev"}
    create_resp = client.post(
        "/strategy-locks",
        json={"surface": None, "scope": "campaign", "title": "Lock", "allowed_actions": ["*"]},
        headers=headers_owner,
    )
    lock_id = create_resp.json()["id"]

    # Create viewer user + membership
    repo = InMemoryIdentityRepository()
    # keep existing data? already set earlier; retrieve current repo
    from engines.identity.state import identity_repo

    repo = identity_repo  # type: ignore
    pwd_hash, salt = hash_password("pw_viewer")
    viewer = User(email="viewer@example.com", password_hash=f"{pwd_hash}:{salt}")
    repo.create_user(viewer)
    repo.create_membership(TenantMembership(tenant_id=tenant_id, user_id=viewer.id, role="viewer"))
    login_resp = client.post("/auth/login", json={"email": "viewer@example.com", "password": "pw_viewer"})
    viewer_token = login_resp.json()["access_token"]
    headers_viewer = {"Authorization": f"Bearer {viewer_token}", "X-Tenant-Id": tenant_id, "X-Env": "dev"}

    approve_resp = client.post(f"/strategy-locks/{lock_id}/approve", headers=headers_viewer)
    assert approve_resp.status_code == 403


def test_tenant_isolation():
    client = _client()
    token_a, tenant_a = _signup_and_login(client, email="a@example.com", tenant_name="TenantA")
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Tenant-Id": tenant_a, "X-Env": "dev"}
    create_resp = client.post(
        "/strategy-locks",
        json={"surface": None, "scope": "campaign", "title": "LockA", "allowed_actions": ["*"]},
        headers=headers_a,
    )
    lock_id = create_resp.json()["id"]

    token_b, tenant_b = _signup_and_login(client, email="b@example.com", tenant_name="TenantB")
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Tenant-Id": tenant_b, "X-Env": "dev"}

    # List should be empty, get should 404
    list_resp = client.get("/strategy-locks", headers=headers_b)
    assert list_resp.status_code == 200
    assert list_resp.json() == []
    get_resp = client.get(f"/strategy-locks/{lock_id}", headers=headers_b)
    assert get_resp.status_code == 404


def test_gated_temperature_and_analytics():
    client = _client()
    token, tenant_id = _signup_and_login(client, email="gate@example.com", tenant_name="Gate")
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-Id": tenant_id, "X-Env": "dev"}

    # Temperature floors blocked without lock
    floor_payload = {"tenant_id": tenant_id, "env": "dev", "surface": "squared", "performance_floors": {"x": 1.0}}
    resp_block = client.put("/temperature/floors", json=floor_payload, headers=headers)
    assert resp_block.status_code == 409

    # Analytics config blocked without lock
    analytics_payload = {"tenant_id": tenant_id, "env": "dev", "surface": "squared", "ga4_measurement_id": "G-123"}
    resp_block2 = client.put(f"/tenants/{tenant_id}/analytics/config", json=analytics_payload, headers=headers)
    assert resp_block2.status_code == 409

    # Create and approve lock allowing both actions
    lock_payload = {
        "surface": "squared",
        "scope": "kpi_corridor",
        "title": "Allow updates",
        "allowed_actions": ["temperature:upsert_floors", "analytics:config_upsert"],
        "valid_from": datetime.now(timezone.utc).isoformat(),
        "valid_until": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    }
    create_resp = client.post("/strategy-locks", json=lock_payload, headers=headers)
    lock_id = create_resp.json()["id"]
    client.post(f"/strategy-locks/{lock_id}/approve", headers=headers)

    resp_ok = client.put("/temperature/floors", json=floor_payload, headers=headers)
    assert resp_ok.status_code == 200
    resp_ok2 = client.put(f"/tenants/{tenant_id}/analytics/config", json=analytics_payload, headers=headers)
    assert resp_ok2.status_code == 200
