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
from engines.page_content.service import set_page_content_service, PageContentService
from engines.page_content.repository import InMemoryPageContentRepository
from engines.strategy_lock.models import ACTION_BUILDER_UPDATE_PAGE, ACTION_BUILDER_PUBLISH_PAGE


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
    user = User(email="page@example.com")
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
    set_page_content_service(PageContentService(repo=InMemoryPageContentRepository()))
    return tenant, headers


def _create_lock(client, headers, actions):
    payload = {"surface": "squared", "scope": "app_toggle", "title": "Allow", "allowed_actions": actions}
    lock_id = client.post("/strategy-locks", json=payload, headers=headers).json()["id"]
    client.post(f"/strategy-locks/{lock_id}/approve", headers=headers)


def test_page_content_crud_and_publish_with_locks():
    tenant, headers = _setup()
    client = TestClient(create_app())
    # No lock -> blocked
    payload = {
        "tenant_id": tenant.id,
        "env": "dev",
        "surface": "squared",
        "slug": "/home",
        "html_or_json": "<h1>Hi</h1>",
    }
    resp_block = client.post("/pages", json=payload, headers=headers)
    assert resp_block.status_code == 409

    _create_lock(client, headers, [ACTION_BUILDER_UPDATE_PAGE, ACTION_BUILDER_PUBLISH_PAGE])
    resp_create = client.post("/pages", json=payload, headers=headers)
    assert resp_create.status_code == 200
    page_id = resp_create.json()["id"]

    resp_get = client.get(f"/pages/{page_id}", headers=headers)
    assert resp_get.status_code == 200

    resp_publish = client.post(f"/pages/{page_id}/publish", headers=headers)
    assert resp_publish.status_code == 200
    assert resp_publish.json()["published"] is True


def test_page_content_tenant_isolation():
    tenant, headers = _setup()
    client = TestClient(create_app())
    _create_lock(client, headers, [ACTION_BUILDER_UPDATE_PAGE])
    payload = {
        "tenant_id": tenant.id,
        "env": "dev",
        "surface": "squared",
        "slug": "/home",
        "html_or_json": "<h1>Hi</h1>",
    }
    client.post("/pages", json=payload, headers=headers)
    other_headers = {"X-Tenant-Id": "t_other", "X-Env": "dev", "Authorization": headers["Authorization"]}
    resp = client.get("/pages", headers=other_headers)
    assert resp.status_code in {400, 403}
