from __future__ import annotations

import os

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.state import set_identity_repo
from engines.identity.models import (
    App,
    ControlPlaneProject,
    Surface,
    Tenant,
    TenantKeyConfig,
    TenantMembership,
    User,
)
from engines.identity.key_service import KeyConfigService
from engines.identity.routes_keys import set_key_service
from engines.common.keys import TenantKeySelector
from engines.identity.jwt_service import JwtService
from engines.strategy_lock.repository import InMemoryStrategyLockRepository
from engines.strategy_lock.service import StrategyLockService, set_strategy_lock_service
from engines.strategy_lock.state import set_strategy_lock_repo
from engines.kpi.service import set_kpi_service, KpiService
from engines.kpi.repository import InMemoryKpiRepository


class NoopStrategyLockService(StrategyLockService):
    def __init__(self) -> None:
        super().__init__(repo=InMemoryStrategyLockRepository())

    def require_strategy_lock_or_raise(self, ctx, surface, action):
        return


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
    surface = repo.create_surface(Surface(tenant_id=tenant.id, name="default"))
    app = repo.create_app(App(tenant_id=tenant.id, name="default"))
    project = repo.create_project(
        ControlPlaneProject(
            tenant_id=tenant.id,
            env="dev",
            project_id="p_demo",
            name="demo",
            default_surface_id=surface.id,
            default_app_id=app.id,
        )
    )
    headers = {
        "X-Tenant-Id": tenant.id,
        "X-Mode": "saas",
        "X-Project-Id": project.project_id,
        "X-Surface-Id": surface.id,
        "X-App-Id": app.id,
        "Authorization": f"Bearer {token}",
    }
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

    set_strategy_lock_service(NoopStrategyLockService())
    resp_corridor = client.put("/kpi/corridors", json=corridor_payload, headers=headers)
    assert resp_corridor.status_code == 200

    resp_list = client.get("/kpi/corridors", params={"surface": "SQUARED²"}, headers=headers)
    assert resp_list.status_code == 200
    assert resp_list.json()

    config_resp = client.get("/kpi/config", params={"surface": "SQUARED²"}, headers=headers)
    assert config_resp.status_code == 200
    config_payload = config_resp.json()
    assert "surface_kpis" in config_payload
    assert isinstance(config_payload["surface_kpis"], list)


def test_kpi_tenant_isolation():
    tenant, headers = _setup()
    client = TestClient(create_app())
    def_payload = {"tenant_id": tenant.id, "env": "dev", "surface": "squared", "name": "weekly_leads", "unit": "count"}
    client.post("/kpi/definitions", json=def_payload, headers=headers)
    other_headers = {"X-Tenant-Id": "t_other", "Authorization": headers["Authorization"]}
    resp = client.get("/kpi/definitions", headers=other_headers)
    assert resp.status_code in {400, 403}


def test_surface_kpi_set_upsert_and_alias_roundtrip():
    tenant, headers = _setup()
    client = TestClient(create_app())

    set_strategy_lock_service(NoopStrategyLockService())

    payload = {
        "tenant_id": tenant.id,
        "env": "dev",
        "surface": "SQUARED²",
        "entries": [
            {
                "name": "profit_after_costs",
                "description": "Net sales minus costs",
                "window_token": "Rolling 7D",
                "comparison_token": "YoY",
                "estimate": False,
            }
        ],
    }
    upsert_resp = client.put("/kpi/surface-kpis", json=payload, headers=headers)
    assert upsert_resp.status_code == 200

    list_resp = client.get("/kpi/surface-kpis", params={"surface": "squared"}, headers=headers)
    assert list_resp.status_code == 200
    assert any(entry["surface"] == "squared2" for entry in list_resp.json())

    config_resp = client.get("/kpi/config", params={"surface": "SQUARED²"}, headers=headers)
    assert config_resp.status_code == 200
    assert config_resp.json().get("surface_kpis")


def test_raw_kpi_ingestion_and_kpi_name_filter():
    tenant, headers = _setup()
    client = TestClient(create_app())

    raw_payload = {
        "tenant_id": tenant.id,
        "env": "dev",
        "surface": "SQUARED²",
        "kpi_name": "weekly_leads",
        "value": 3.2,
        "exact": True,
        "app_id": "app1",
        "project_id": "p_demo",
    }
    resp = client.post("/kpi/raw", json=raw_payload, headers=headers)
    assert resp.status_code == 200

    all_resp = client.get("/kpi/raw", params={"surface": "squared"}, headers=headers)
    assert all_resp.status_code == 200
    assert all_resp.json()

    filtered_resp = client.get(
        "/kpi/raw",
        params={"surface": "squared", "kpi_name": "weekly_leads"},
        headers=headers,
    )
    assert filtered_resp.status_code == 200
    assert filtered_resp.json()
    assert all(item["kpi_name"] == "weekly_leads" for item in filtered_resp.json())
