from __future__ import annotations

import os

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.identity.state import set_identity_repo
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.models import TenantKeyConfig, TenantMembership, Tenant, User
from engines.identity.key_service import KeyConfigService
from engines.identity.routes_keys import set_key_service
from engines.common.keys import TenantKeySelector
from engines.identity.jwt_service import JwtService
from engines.strategy_lock.repository import InMemoryStrategyLockRepository
from engines.strategy_lock.service import StrategyLockService, set_strategy_lock_service
from engines.strategy_lock.state import set_strategy_lock_repo


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
    user_owner = User(email="owner@example.com")
    user_viewer = User(email="viewer@example.com")
    repo.create_tenant(tenant)
    repo.create_user(user_owner)
    repo.create_user(user_viewer)
    repo.create_membership(TenantMembership(tenant_id=tenant.id, user_id=user_owner.id, role="owner"))
    repo.create_membership(TenantMembership(tenant_id=tenant.id, user_id=user_viewer.id, role="viewer"))
    selector = TenantKeySelector(repo)
    jwt = JwtService(selector)
    token_owner = jwt.issue_token(
        {
            "sub": user_owner.id,
            "email": user_owner.email,
            "tenant_ids": [tenant.id],
            "default_tenant_id": tenant.id,
            "role_map": {tenant.id: "owner"},
        }
    )
    token_viewer = jwt.issue_token(
        {
            "sub": user_viewer.id,
            "email": user_viewer.email,
            "tenant_ids": [tenant.id],
            "default_tenant_id": tenant.id,
            "role_map": {tenant.id: "viewer"},
        }
    )
    sl_repo = InMemoryStrategyLockRepository()
    set_strategy_lock_repo(sl_repo)
    set_strategy_lock_service(StrategyLockService(sl_repo))
    return tenant, token_owner, token_viewer


def test_protected_key_routes_enforce_roles():
    tenant, token_owner, token_viewer = _setup()
    client = TestClient(create_app())
    headers_owner = {
        "X-Tenant-Id": tenant.id,
        "X-Mode": "saas",
        "X-Project-Id": "p_demo",
        "Authorization": f"Bearer {token_owner}",
    }
    payload = {
        "slot": "llm_primary",
        "env": "dev",
        "provider": "openai",
        "secret_value": "sk-123",
    }
    resp = client.post(f"/tenants/{tenant.id}/keys", json=payload, headers=headers_owner)
    assert resp.status_code == 200

    headers_viewer = {
        "X-Tenant-Id": tenant.id,
        "X-Mode": "saas",
        "X-Project-Id": "p_demo",
        "Authorization": f"Bearer {token_viewer}",
    }
    resp = client.get(f"/tenants/{tenant.id}/keys", headers=headers_viewer)
    assert resp.status_code == 403


def test_temperature_config_requires_admin():
    tenant, token_owner, token_viewer = _setup()
    client = TestClient(create_app())
    payload = {
        "tenant_id": tenant.id,
        "env": "dev",
        "surface": "squared",
        "performance_floors": {"weekly_leads": 10},
        "cadence_floors": {},
    }
    headers_owner = {
        "X-Tenant-Id": tenant.id,
        "X-Mode": "saas",
        "X-Project-Id": "p_demo",
        "Authorization": f"Bearer {token_owner}",
    }
    headers_viewer = {
        "X-Tenant-Id": tenant.id,
        "X-Mode": "saas",
        "X-Project-Id": "p_demo",
        "Authorization": f"Bearer {token_viewer}",
    }

    # add strategy lock to allow owner action
    lock_payload = {"surface": "squared", "scope": "kpi_corridor", "title": "allow temp", "allowed_actions": ["temperature:upsert_floors"]}
    lock_resp = client.post("/strategy-locks", json=lock_payload, headers=headers_owner)
    lock_id = lock_resp.json()["id"]
    client.post(f"/strategy-locks/{lock_id}/approve", headers=headers_owner)

    resp = client.put("/temperature/floors", json=payload, headers=headers_owner)
    assert resp.status_code == 200

    resp = client.put("/temperature/floors", json=payload, headers=headers_viewer)
    assert resp.status_code == 403
