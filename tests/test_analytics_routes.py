from __future__ import annotations

import os

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.common.analytics import AnalyticsResolver, get_analytics_resolver, set_analytics_resolver
from engines.common.identity import RequestContext
from engines.identity.analytics_service import AnalyticsConfigService, get_analytics_service, set_analytics_service
from engines.identity.models import TenantAnalyticsConfig
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.state import set_identity_repo
from engines.strategy_lock.repository import InMemoryStrategyLockRepository
from engines.strategy_lock.service import StrategyLockService, set_strategy_lock_service
from engines.strategy_lock.state import set_strategy_lock_repo


def setup_function(_fn):
    set_identity_repo(InMemoryIdentityRepository())
    set_analytics_service(AnalyticsConfigService())
    set_analytics_resolver(AnalyticsResolver(service=get_analytics_service()))
    sl_repo = InMemoryStrategyLockRepository()
    set_strategy_lock_repo(sl_repo)
    set_strategy_lock_service(StrategyLockService(sl_repo))
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


def test_owner_can_upsert_and_read_analytics_config():
    client = TestClient(create_app())
    token, tenant_id = _signup_and_login(client)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": tenant_id,
        "X-Mode": "saas",
        "X-Project-Id": "p_demo",
    }

    # Strategy lock to allow config updates
    lock_payload = {
        "surface": "squared",
        "scope": "kpi_corridor",
        "title": "Allow analytics",
        "allowed_actions": ["analytics:config_upsert"],
    }
    lock_resp = client.post("/strategy-locks", json=lock_payload, headers=headers)
    lock_id = lock_resp.json()["id"]
    client.post(f"/strategy-locks/{lock_id}/approve", headers=headers)

    payload = {
        "tenant_id": tenant_id,
        "env": "dev",
        "surface": "squared",
        "ga4_measurement_id": "G-TEST",
        "meta_pixel_id": "META123",
    }
    put_resp = client.put(f"/tenants/{tenant_id}/analytics/config", json=payload, headers=headers)
    assert put_resp.status_code == 200

    list_resp = client.get(f"/tenants/{tenant_id}/analytics/config", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()[0]["ga4_measurement_id"] == "G-TEST"

    current_resp = client.get(
        f"/tenants/{tenant_id}/analytics/config/current",
        params={"env": "dev", "surface": "squared"},
        headers=headers,
    )
    assert current_resp.status_code == 200
    assert current_resp.json()["tenant_id"] == tenant_id


def test_analytics_falls_back_to_system_config():
    client = TestClient(create_app())
    token, tenant_id = _signup_and_login(client)
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": tenant_id,
        "X-Mode": "saas",
        "X-Project-Id": "p_demo",
    }

    # Only system config exists
    svc = get_analytics_service()
    svc.upsert_config(
        TenantAnalyticsConfig(
            tenant_id="system",
            env="prod",
            surface="squared",
            ga4_measurement_id="G-SYSTEM",
        )
    )
    resp = client.get(
        f"/tenants/{tenant_id}/analytics/config/current",
        params={"env": "dev", "surface": "squared"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ga4_measurement_id"] == "G-SYSTEM"
    assert body["tenant_id"] == "system"

    # Resolver reports source=system
    resolver: AnalyticsResolver = get_analytics_resolver()
    ctx = RequestContext(tenant_id=tenant_id, mode="saas", project_id="p_demo", user_id="u1")
    effective = resolver.resolve(ctx, "squared")
    assert effective is not None
    assert effective.ga4_measurement_id == "G-SYSTEM"
    assert effective.source == "system"
