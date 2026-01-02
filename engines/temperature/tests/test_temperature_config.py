import os
import shutil
import tempfile
from typing import Optional

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.identity.jwt_service import default_jwt_service
from engines.identity.models import App, ControlPlaneProject, Surface, Tenant, TenantMembership
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.state import set_identity_repo
from engines.strategy_lock.repository import InMemoryStrategyLockRepository
from engines.strategy_lock.service import StrategyLockService, set_strategy_lock_service
from engines.temperature.repository import FileTemperatureRepository
from engines.temperature.service import TemperatureService, set_temperature_service

DEFAULT_TENANT_ID = "t_temp"
DEFAULT_ENV = "dev"
DEFAULT_PROJECT_ID: str = ""
DEFAULT_SURFACE_ID: str = ""
DEFAULT_APP_ID: str = ""
TEMP_REPO_ROOT: Optional[str] = None


class NoopStrategyLockService(StrategyLockService):
    def __init__(self) -> None:
        super().__init__(repo=InMemoryStrategyLockRepository())

    def require_strategy_lock_or_raise(self, ctx, surface, action):
        return


def setup_module(_module):
    global DEFAULT_PROJECT_ID, DEFAULT_SURFACE_ID, DEFAULT_APP_ID, TEMP_REPO_ROOT
    os.environ.setdefault("AUTH_JWT_SIGNING", "temp-secret")
    os.environ.setdefault("APP_ENV", DEFAULT_ENV)
    repo = InMemoryIdentityRepository()
    set_identity_repo(repo)
    tenant = Tenant(id=DEFAULT_TENANT_ID, name="Temperature tenant")
    repo.create_tenant(tenant)
    repo.create_membership(TenantMembership(tenant_id=tenant.id, user_id="temp-user", role="member"))
    surface = repo.create_surface(Surface(tenant_id=tenant.id, name="default"))
    app = repo.create_app(App(tenant_id=tenant.id, name="default"))
    project = repo.create_project(
        ControlPlaneProject(
            tenant_id=tenant.id,
            env=DEFAULT_ENV,
            project_id="p_temp",
            name="temp-project",
            default_surface_id=surface.id,
            default_app_id=app.id,
        )
    )
    DEFAULT_PROJECT_ID = project.project_id
    DEFAULT_SURFACE_ID = surface.id
    DEFAULT_APP_ID = app.id
    TEMP_REPO_ROOT = tempfile.mkdtemp(prefix="temperature_repo_")
    set_temperature_service(TemperatureService(repo=FileTemperatureRepository(root=TEMP_REPO_ROOT)))
    set_strategy_lock_service(NoopStrategyLockService())


def teardown_module(_module):
    if TEMP_REPO_ROOT:
        shutil.rmtree(TEMP_REPO_ROOT, ignore_errors=True)


def _auth_token(tenant_id: str = DEFAULT_TENANT_ID, user_id: str = "temp-user"):
    svc = default_jwt_service()
    claims = {
        "sub": user_id,
        "email": f"{user_id}@example.com",
        "tenant_ids": [tenant_id],
        "default_tenant_id": tenant_id,
        "role_map": {tenant_id: "owner"},
    }
    return svc.issue_token(claims)


def _auth_headers(tenant_id: str = DEFAULT_TENANT_ID, env: str = DEFAULT_ENV, request_id: str = "req-temp"):
    token = _auth_token(tenant_id=tenant_id)
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": tenant_id,
        "X-Mode": "saas",
        "X-Project-Id": DEFAULT_PROJECT_ID,
        "X-Surface-Id": DEFAULT_SURFACE_ID,
        "X-App-Id": DEFAULT_APP_ID,
        "X-Request-Id": request_id,
    }


def test_temperature_config_requires_auth():
    client = TestClient(create_app())
    headers = {
        "X-Tenant-Id": DEFAULT_TENANT_ID,
        "X-Mode": "saas",
        "X-Project-Id": DEFAULT_PROJECT_ID,
        "X-Surface-Id": DEFAULT_SURFACE_ID,
        "X-App-Id": DEFAULT_APP_ID,
        "X-Request-Id": "req-no-auth",
    }
    resp = client.get("/temperature/config", params={"surface": "flat"}, headers=headers)
    assert resp.status_code == 401


def test_temperature_config_requires_membership():
    client = TestClient(create_app())
    headers = _auth_headers()
    headers["X-Tenant-Id"] = "t_other"
    resp = client.get("/temperature/config", params={"surface": "flat"}, headers=headers)
    assert resp.status_code == 403


def test_temperature_config_returns_data_for_member():
    client = TestClient(create_app())
    headers = _auth_headers()
    resp = client.get("/temperature/config", params={"surface": "flat"}, headers=headers)
    assert resp.status_code == 200
    assert "floors" in resp.json()


def test_temperature_config_alias_roundtrip():
    client = TestClient(create_app())
    headers = _auth_headers()
    floors_payload = {
        "tenant_id": DEFAULT_TENANT_ID,
        "env": DEFAULT_ENV,
        "surface": "squared",
        "performance_floors": {"weekly_leads": 5},
        "cadence_floors": {"email_campaigns_per_week": 1},
    }
    ceilings_payload = {
        "tenant_id": DEFAULT_TENANT_ID,
        "env": DEFAULT_ENV,
        "surface": "squared",
        "ceilings": {"weekly_leads": 100},
    }
    weights_payload = {
        "tenant_id": DEFAULT_TENANT_ID,
        "env": DEFAULT_ENV,
        "surface": "squared",
        "weights": {"weekly_leads": 1.0},
        "source": "tenant_override",
    }
    assert client.put("/temperature/floors", json=floors_payload, headers=headers).status_code == 200
    assert client.put("/temperature/ceilings", json=ceilings_payload, headers=headers).status_code == 200
    assert client.put("/temperature/weights", json=weights_payload, headers=headers).status_code == 200

    alias_resp = client.get("/temperature/config", params={"surface": "SQUARED²"}, headers=headers)
    assert alias_resp.status_code == 200
    alias_data = alias_resp.json()
    assert alias_data["floors"]["performance_floors"].get("weekly_leads") == 5
    assert alias_data["ceilings"]["ceilings"].get("weekly_leads") == 100
    assert alias_data["weights"]["weights"].get("weekly_leads") == 1.0


def test_temperature_weights_independent_of_floor_and_ceilings():
    client = TestClient(create_app())
    headers = _auth_headers()
    floors_payload = {
        "tenant_id": DEFAULT_TENANT_ID,
        "env": DEFAULT_ENV,
        "surface": "squared",
        "performance_floors": {"weekly_leads": 5},
    }
    ceilings_payload = {
        "tenant_id": DEFAULT_TENANT_ID,
        "env": DEFAULT_ENV,
        "surface": "squared",
        "ceilings": {"weekly_leads": 100},
    }
    assert client.put("/temperature/floors", json=floors_payload, headers=headers).status_code == 200
    assert client.put("/temperature/ceilings", json=ceilings_payload, headers=headers).status_code == 200

    before = client.get("/temperature/config", params={"surface": "SQUARED²"}, headers=headers).json()
    assert before["floors"].get("performance_floors")
    assert before["ceilings"].get("ceilings")

    new_weights_payload = {
        "tenant_id": DEFAULT_TENANT_ID,
        "env": DEFAULT_ENV,
        "surface": "SQUARED²",
        "weights": {"weekly_leads": 2.5},
        "source": "tenant_override",
    }
    client.put("/temperature/weights", json=new_weights_payload, headers=headers)

    after = client.get("/temperature/config", params={"surface": "SQUARED²"}, headers=headers).json()
    assert after["floors"] == before["floors"]
    assert after["ceilings"] == before["ceilings"]
    assert after["weights"]["weights"]["weekly_leads"] == 2.5
