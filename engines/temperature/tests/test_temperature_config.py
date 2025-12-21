import os

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.identity.jwt_service import default_jwt_service
from engines.temperature.repository import InMemoryTemperatureRepository
from engines.temperature.service import TemperatureService, set_temperature_service


def setup_module(_module):
    os.environ.setdefault("AUTH_JWT_SIGNING", "temp-secret")
    os.environ.setdefault("APP_ENV", "dev")
    set_temperature_service(TemperatureService(repo=InMemoryTemperatureRepository()))


def _auth_token(tenant_id: str = "t_temp", user_id: str = "temp-user"):
    svc = default_jwt_service()
    claims = {
        "sub": user_id,
        "email": f"{user_id}@example.com",
        "tenant_ids": [tenant_id],
        "default_tenant_id": tenant_id,
        "role_map": {tenant_id: "member"},
    }
    return svc.issue_token(claims)


def _auth_headers(tenant_id: str = "t_temp", env: str = "dev", request_id: str = "req-temp"):
    token = _auth_token(tenant_id=tenant_id)
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": tenant_id,
        "X-Env": env,
        "X-Request-Id": request_id,
    }


def test_temperature_config_requires_auth():
    client = TestClient(create_app())
    headers = {
        "X-Tenant-Id": "t_temp",
        "X-Env": "dev",
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
