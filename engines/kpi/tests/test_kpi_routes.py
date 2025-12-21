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
from engines.kpi.service import set_kpi_service, KpiService
from engines.kpi.repository import InMemoryKpiRepository


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
    user = User(email="kpi@example.com")
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
    set_kpi_service(KpiService(repo=InMemoryKpiRepository()))
    return tenant, headers


def test_kpi_definition_and_corridor_with_strategy_lock():
    tenant, headers = _setup()
    client = TestClient(create_app())

    def_payload = {"tenant_id": tenant.id, "env": "dev", "surface": "squared", "name": "weekly_leads", "unit": "count"}
    resp_def = client.post("/kpi/definitions", json=def_payload, headers=headers)
    assert resp_def.status_code == 200

    # corridor blocked without lock
    corridor_payload = {
        "tenant_id": tenant.id,
        "env": "dev",
        "surface": "squared",
        "kpi_name": "weekly_leads",
        "floor": 10.0,
    }
    resp_block = client.put("/kpi/corridors", json=corridor_payload, headers=headers)
    assert resp_block.status_code == 409

    # create strategy lock and approve
    lock_payload = {
        "surface": "squared",
        "scope": "kpi_corridor",
        "title": "Allow KPI updates",
        "allowed_actions": ["kpi:corridor_upsert"],
    }
    lock_resp = client.post("/strategy-locks", json=lock_payload, headers=headers)
    lock_id = lock_resp.json()["id"]
    client.post(f"/strategy-locks/{lock_id}/approve", headers=headers)

    resp_corridor = client.put("/kpi/corridors", json=corridor_payload, headers=headers)
    assert resp_corridor.status_code == 200

    resp_list = client.get("/kpi/corridors", headers=headers)
    assert resp_list.status_code == 200
    assert resp_list.json()


def test_kpi_tenant_isolation():
    tenant, headers = _setup()
    client = TestClient(create_app())
    def_payload = {"tenant_id": tenant.id, "env": "dev", "surface": "squared", "name": "weekly_leads", "unit": "count"}
    client.post("/kpi/definitions", json=def_payload, headers=headers)
    other_headers = {"X-Tenant-Id": "t_other", "X-Env": "dev", "Authorization": headers["Authorization"]}
    resp = client.get("/kpi/definitions", headers=other_headers)
    assert resp.status_code in {400, 403}
