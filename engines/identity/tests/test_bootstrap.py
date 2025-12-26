import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from engines.identity.routes_auth import router
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.state import set_identity_repo

# Setup test app
from fastapi import FastAPI
app = FastAPI()
app.include_router(router)

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_repo():
    repo = InMemoryIdentityRepository()
    set_identity_repo(repo)
    return repo

def test_bootstrap_tenants_success():
    with patch.dict(os.environ, {"SYSTEM_BOOTSTRAP_KEY": "secret-123"}):
        response = client.post(
            "/auth/bootstrap/tenants",
            headers={"X-System-Key": "secret-123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "t_system" in data["created"]
        assert "t_northstar" not in data["created"]

        # Verify idempotency
        response = client.post(
            "/auth/bootstrap/tenants",
            headers={"X-System-Key": "secret-123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created"] == []

def test_bootstrap_tenants_invalid_key():
    with patch.dict(os.environ, {"SYSTEM_BOOTSTRAP_KEY": "secret-123"}):
        response = client.post(
            "/auth/bootstrap/tenants",
            headers={"X-System-Key": "wrong-key"}
        )
        assert response.status_code == 403

def test_bootstrap_tenants_no_env_var():
    # If env var not set, should default direct fail
    with patch.dict(os.environ, {}, clear=True):
         response = client.post(
            "/auth/bootstrap/tenants",
            headers={"X-System-Key": "any"}
        )
         assert response.status_code == 403

def test_bootstrap_tenants_system_only():
    """Verify that bootstrap creates only t_system, not t_northstar."""
    with patch.dict(os.environ, {"SYSTEM_BOOTSTRAP_KEY": "secret-123"}):
        response = client.post(
            "/auth/bootstrap/tenants",
            headers={"X-System-Key": "secret-123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created"] == ["t_system"]
        # Confirm t_northstar does NOT exist
        assert len([t for t in data["created"] if "northstar" in t.lower()]) == 0

