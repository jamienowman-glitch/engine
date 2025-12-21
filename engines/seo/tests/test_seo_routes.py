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
from engines.strategy_lock.repository import InMemoryStrategyLockRepository
from engines.strategy_lock.service import StrategyLockService, set_strategy_lock_service
from engines.strategy_lock.state import set_strategy_lock_repo
from engines.seo.service import set_seo_service, SeoService
from engines.seo.repository import InMemorySeoRepository


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
    user = User(email="seo@example.com")
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
    sl_repo = InMemoryStrategyLockRepository()
    set_strategy_lock_repo(sl_repo)
    set_strategy_lock_service(StrategyLockService(sl_repo))
    set_seo_service(SeoService(repo=InMemorySeoRepository()))
    return tenant, headers


def test_seo_upsert_requires_strategy_lock():
    tenant, headers = _setup()
    client = TestClient(create_app())
    payload = {
        "tenant_id": tenant.id,
        "env": "dev",
        "surface": "squared",
        "page_type": "home",
        "title": "Home",
        "description": "Desc",
    }
    resp_block = client.put("/seo/pages", json=payload, headers=headers)
    assert resp_block.status_code == 409

    lock_payload = {
        "surface": "squared",
        "scope": "kpi_corridor",
        "title": "Allow SEO",
        "allowed_actions": ["seo_page_config_update"],
    }
    lock_resp = client.post("/strategy-locks", json=lock_payload, headers=headers)
    lock_id = lock_resp.json()["id"]
    client.post(f"/strategy-locks/{lock_id}/approve", headers=headers)

    resp_ok = client.put("/seo/pages", json=payload, headers=headers)
    assert resp_ok.status_code == 200

    resp_get = client.get("/seo/pages/squared/home", headers=headers)
    assert resp_get.status_code == 200
    assert resp_get.json()["title"] == "Home"


def test_seo_tenant_isolation():
    tenant, headers = _setup()
    client = TestClient(create_app())
    lock_payload = {
        "surface": "squared",
        "scope": "kpi_corridor",
        "title": "Allow SEO",
        "allowed_actions": ["seo_page_config_update"],
    }
    lock_id = client.post("/strategy-locks", json=lock_payload, headers=headers).json()["id"]
    client.post(f"/strategy-locks/{lock_id}/approve", headers=headers)
    payload = {
        "tenant_id": tenant.id,
        "env": "dev",
        "surface": "squared",
        "page_type": "home",
        "title": "Home",
        "description": "Desc",
    }
    client.put("/seo/pages", json=payload, headers=headers)
    other_headers = {"X-Tenant-Id": "t_other", "X-Env": "dev", "Authorization": headers["Authorization"]}
    resp = client.get("/seo/pages", headers=other_headers)
    assert resp.status_code in {400, 403}
