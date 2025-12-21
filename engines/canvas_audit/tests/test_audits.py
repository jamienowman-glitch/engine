import pytest
from fastapi.testclient import TestClient
from engines.canvas_audit.router import router as audit_router
from engines.identity.auth import get_auth_context, AuthContext
from engines.common.identity import get_request_context, RequestContext
from fastapi import FastAPI
import asyncio # Not used directly if we use TestClient, but imported if needed

app = FastAPI()
app.include_router(audit_router)
client = TestClient(app)

# Mocks
async def mock_auth_ctx():
    return AuthContext(
        user_id="u_audit",
        email="test@example.com",
        tenant_ids=["t_test"],
        default_tenant_id="t_test",
        role_map={"t_test": "member"}
    )

async def mock_req_ctx():
    return RequestContext(tenant_id="t_test", env="dev", user_id="u_audit")

app.dependency_overrides[get_auth_context] = mock_auth_ctx
app.dependency_overrides[get_request_context] = mock_req_ctx

def test_audit_happy_path():
    payload = {"ruleset": "standard"}
    # Note: this calls underlying 'upload_artifact' which uses InMemoryStorage singleton from canvas_artifacts
    resp = client.post("/canvas/c1/audits", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["findings"] == []
    assert data["score"] == 1.0
    assert data["artifact_ref_id"] is not None

def test_audit_tenant_mismatch():
    async def bad_auth():
        return AuthContext(
            user_id="u_bad",
            tenant_ids=["t_bad"],
            default_tenant_id="t_bad",
            email="bad", role_map={}
        )
    app.dependency_overrides[get_auth_context] = bad_auth
    
    resp = client.post("/canvas/c1/audits", json={})
    assert resp.status_code == 403
