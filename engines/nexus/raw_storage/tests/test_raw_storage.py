"""Tests for Raw Storage Engine."""
import os
from unittest import mock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from engines.common.identity import RequestContext
from engines.identity.jwt_service import default_jwt_service
from engines.nexus.raw_storage.repository import S3RawStorageRepository
from engines.nexus.raw_storage.service import RawStorageService
from engines.nexus.raw_storage.routes import router


os.environ.setdefault("AUTH_JWT_SIGNING", "phase2-secret")
os.environ.setdefault("RAW_BUCKET", "test-raw-bucket")


def _auth_token(tenant_id: str = "t_demo", user_id: str = "u_demo"):
    svc = default_jwt_service()
    claims = {
        "sub": user_id,
        "email": f"{user_id}@example.com",
        "tenant_ids": [tenant_id],
        "default_tenant_id": tenant_id,
        "role_map": {tenant_id: "owner"},
    }
    return svc.issue_token(claims)


def _auth_headers(tenant_id: str = "t_demo", request_tenant: str | None = None):
    return {
        "Authorization": f"Bearer {_auth_token(tenant_id=tenant_id)}",
        "X-Tenant-Id": request_tenant or tenant_id,
        "X-Env": "dev",
    }


def test_s3_key_tenancy():
    """Verify S3 keys are strictly tenant-scoped."""
    repo = S3RawStorageRepository(bucket_name="test-bucket")
    key = repo._get_key("t_demo", "dev", "asset123", "file.txt")
    assert key == "tenants/t_demo/dev/raw/asset123/file.txt"


def test_s3_generate_presigned(monkeypatch):
    """Verify presigned post generation structure."""
    repo = S3RawStorageRepository(bucket_name="test-bucket")
    
    # Mock boto3 client
    mock_s3 = mock.MagicMock()
    mock_s3.generate_presigned_post.return_value = {
        "url": "https://s3.amazonaws.com/test-bucket",
        "fields": {"key": "tenants/t_demo/dev/raw/asset123/file.txt"}
    }
    
    with mock.patch("boto3.client", return_value=mock_s3):
        url, fields = repo.generate_presigned_post("t_demo", "dev", "asset123", "file.txt", "text/plain")
    
    assert url == "https://s3.amazonaws.com/test-bucket"
    assert fields["key"] == "tenants/t_demo/dev/raw/asset123/file.txt"


def test_service_presign_upload():
    """Verify service layer returns correct structure + logs event."""
    repo = mock.MagicMock()
    repo.generate_presigned_post.return_value = ("http://fake/url", {"field": "val"})
    
    service = RawStorageService(repo=repo)
    ctx = RequestContext(tenant_id="t_test", env="dev", user_id="u_user", request_id="req1")
    
    # Mock logger
    with mock.patch("engines.nexus.raw_storage.service.default_event_logger") as mock_log:
        result = service.presign_upload(ctx, "data.csv", "text/csv")
    
    assert result["url"] == "http://fake/url"
    assert "asset_id" in result
    
    # Verify event logged
    assert mock_log.call_count == 1
    entry = mock_log.call_args[0][0]
    assert entry.event_type == "raw_asset_presigned"
    assert entry.tenant_id == "t_test"


def test_routes_smoke():
    """Smoke test that routes are mountable and 422 if body missing."""
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    # Expect 401 because auth dependency runs before body validation
    headers = {"X-Tenant-Id": "t_demo", "X-Env": "dev"}
    response = client.post("/nexus/raw/presign-upload", json={}, headers=headers)
    assert response.status_code == 401


def test_presign_requires_auth():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    headers = {"X-Tenant-Id": "t_demo", "X-Env": "dev"}
    response = client.post("/nexus/raw/presign-upload", json={"filename": "data.csv"}, headers=headers)
    assert response.status_code == 401


def test_presign_rejects_cross_tenant():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    headers = _auth_headers(tenant_id="t_beta", request_tenant="t_alpha")
    response = client.post("/nexus/raw/presign-upload", json={"filename": "data.csv"}, headers=headers)
    assert response.status_code == 403


def test_presign_allows_valid_tenant():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    headers = _auth_headers()
    with mock.patch("engines.nexus.hardening.gate_chain.GateChain.run"):
        with mock.patch(
            "engines.nexus.raw_storage.repository.S3RawStorageRepository.generate_presigned_post"
        ) as mock_generate:
            mock_generate.return_value = (
                "https://fake.s3.amazonaws.com/test-raw-bucket",
                {"key": "value"},
            )

            response = client.post(
                "/nexus/raw/presign-upload",
                json={"filename": "data.csv"},
                headers=headers,
            )
    assert response.status_code == 200
    data = response.json()
    assert data["asset_id"]


def test_get_key_prefix():
    repo = S3RawStorageRepository(bucket_name="test-raw-bucket")
    key = repo._get_key("t_alpha", "dev", "asset123", "file.txt")
    assert key.startswith("tenants/t_alpha/dev/raw/")
    assert key.endswith("file.txt")


def test_get_key_invalid_tenant():
    repo = S3RawStorageRepository(bucket_name="test-raw-bucket")
    with pytest.raises(HTTPException):
        repo._get_key("bad-tenant", "dev", "asset123", "file.txt")


def test_get_key_invalid_env():
    repo = S3RawStorageRepository(bucket_name="test-raw-bucket")
    with pytest.raises(HTTPException):
        repo._get_key("t_alpha", "invalid", "asset123", "file.txt")


def test_generate_presign_missing_bucket(monkeypatch):
    """Missing RAW_BUCKET config should raise early."""
    monkeypatch.delenv("RAW_BUCKET", raising=False)
    repo = S3RawStorageRepository()
    with pytest.raises(HTTPException):
        repo.generate_presigned_post("t_demo", "dev", "asset123", "file.txt", "text/plain")


def test_register_emits_event():
    repo = S3RawStorageRepository(bucket_name="test-raw-bucket")
    service = RawStorageService(repo=repo)
    ctx = RequestContext(tenant_id="t_demo", env="dev", user_id="u_user", request_id="trace-123")

    with mock.patch("engines.nexus.raw_storage.service.default_event_logger") as mock_log:
        service.register_asset(ctx, "asset123", "file.txt", "text/plain", size_bytes=42)

    assert mock_log.call_count == 1
    entry = mock_log.call_args[0][0]
    assert entry.metadata["uri"].startswith("s3://")
    assert entry.request_id == "trace-123"
    assert entry.trace_id == "trace-123"


def test_register_persists_metadata():
    from engines.nexus.raw_storage.repository import InMemoryRawStorageRepository
    repo = InMemoryRawStorageRepository()
    service = RawStorageService(repo=repo)
    ctx = RequestContext(tenant_id="t_demo", env="dev", user_id="u_user", request_id="trace-123")

    with mock.patch("engines.nexus.raw_storage.service.default_event_logger"):
        asset = service.register_asset(ctx, "asset999", "data.json", "application/json")
    
    # Check return val
    assert asset.asset_id == "asset999"
    
    # Check persistence
    stored = repo.metadata_store.get("asset999")
    assert stored is not None
    assert stored.asset_id == "asset999"
    assert stored.filename == "data.json"

def test_missing_bucket_raises():
    """Test that S3RawStorageRepository fails when bucket is not configured on usage."""
    # Temporarily clear RAW_BUCKET and create repo
    with mock.patch.dict(os.environ, {"RAW_BUCKET": ""}, clear=False):
        repo = S3RawStorageRepository(bucket_name=None)
        
        # Try to generate presigned URL without bucket - should fail
        with pytest.raises(HTTPException, match="RAW_BUCKET config missing"):
            repo.generate_presigned_post("t_demo", "dev", "asset123", "file.txt", "text/plain")
