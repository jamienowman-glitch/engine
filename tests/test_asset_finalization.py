import pytest
from fastapi.testclient import TestClient
from engines.workbench.routes import router
from engines.common.identity import RequestContext
from fastapi import FastAPI, Depends

# Setup minimal app for testing router
app = FastAPI()
app.include_router(router)

# Mock Deps
from engines.identity.auth import get_auth_context
from engines.common.identity import get_request_context
from unittest.mock import MagicMock

def mock_get_request_context():
    return RequestContext(tenant_id="t_test", env="dev", mode="lab", user_id="u1")

def mock_get_auth_context():
    mock = MagicMock()
    mock.tenant_id = "t_test"
    mock.tenant_ids = ["t_test"]
    mock.roles = ["admin"]
    return mock

app.dependency_overrides[get_request_context] = mock_get_request_context
app.dependency_overrides[get_auth_context] = mock_get_auth_context

client = TestClient(app)

def test_finalize_pii_asset():
    response = client.post(
        "/workbench/assets/finalize",
        json={"asset_id": "pii_12345", "destination": "email"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "finalized"
    assert "rehydrated/pii_12345" in data["url"]

def test_finalize_regular_asset():
    response = client.post(
        "/workbench/assets/finalize",
        json={"asset_id": "file_abc"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
