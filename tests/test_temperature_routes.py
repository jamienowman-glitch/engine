from __future__ import annotations

from fastapi.testclient import TestClient
import os

from engines.chat.service.server import create_app
from engines.temperature.service import set_temperature_service, TemperatureService
from engines.temperature.repository import InMemoryTemperatureRepository
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


def _client():
    # shared identity + jwt secret
    os.environ["APP_ENV"] = "dev"
    os.environ["AUTH_JWT_SIGNING"] = "secret"
    repo = InMemoryIdentityRepository()
    set_identity_repo(repo)
    set_key_service(KeyConfigService(repo=repo))
    repo.set_key_config(
        TenantKeyConfig(
            tenant_id="system",
            env="prod",
            slot="auth_jwt_signing",
            provider="system",
            secret_name="AUTH_JWT_SIGNING",
        )
    )
    tenant = Tenant(id="t_demo", name="Demo")
    user = User(email="temp@example.com")
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
    headers = {
        "X-Tenant-Id": tenant.id,
        "X-Mode": "saas",
        "X-Project-Id": "p_demo",
        "Authorization": f"Bearer {token}",
    }
    set_temperature_service(TemperatureService(repo=InMemoryTemperatureRepository()))
    sl_repo = InMemoryStrategyLockRepository()
    set_strategy_lock_repo(sl_repo)
    set_strategy_lock_service(StrategyLockService(sl_repo))
    return TestClient(create_app()), headers, tenant


def test_upsert_and_get_config_and_current():
    client, headers, tenant = _client()
    lock_payload = {
        "surface": "squared",
        "scope": "kpi_corridor",
        "title": "Allow temp edits",
        "allowed_actions": ["temperature:upsert_floors", "temperature:upsert_ceilings", "temperature:upsert_weights"],
    }
    lock_resp = client.post("/strategy-locks", json=lock_payload, headers=headers)
    lock_id = lock_resp.json()["id"]
    client.post(f"/strategy-locks/{lock_id}/approve", headers=headers)
    floor = {
        "tenant_id": headers["X-Tenant-Id"],
        "env": "dev",
        "surface": "squared",
        "performance_floors": {"weekly_leads": 50},
        "cadence_floors": {"email_campaigns_per_week": 3},
    }
    resp = client.put("/temperature/floors", json=floor, headers=headers)
    assert resp.status_code == 200

    ceiling = {
        "tenant_id": "t_demo",
        "env": "dev",
        "surface": "squared",
        "ceilings": {"complaint_rate": 0.05},
    }
    resp = client.put("/temperature/ceilings", json=ceiling, headers=headers)
    assert resp.status_code == 200

    weights = {
        "tenant_id": "t_demo",
        "env": "dev",
        "surface": "squared",
        "weights": {"weekly_leads": 1.0},
        "source": "tenant_override",
    }
    resp = client.put("/temperature/weights", json=weights, headers=headers)
    assert resp.status_code == 200

    # config fetch
    resp = client.get("/temperature/config", params={"surface": "squared"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["floors"]["performance_floors"]["weekly_leads"] == 50

    # current temperature
    resp = client.get("/temperature/current", params={"surface": "squared", "window_days": 7}, headers=headers)
    assert resp.status_code == 200
    current = resp.json()
    assert current["surface"] == "squared"
    assert "value" in current

    # history listing
    resp = client.get("/temperature/history", params={"surface": "squared"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["items"]
