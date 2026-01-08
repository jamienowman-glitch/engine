import os
from io import BytesIO

from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.identity.models import App, Surface
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.state import set_identity_repo
from engines.identity.jwt_service import default_jwt_service
from engines.media_v2.routes import (
    register_error_handlers as register_media_error_handlers,
    router as media_router,
)
from engines.media_v2.service import InMemoryMediaRepository, MediaService, set_media_service

_client: TestClient | None = None


class StubS3Storage:
    def __init__(self):
        self.uploads = []

    def upload_bytes(self, tenant_id, env, asset_id, filename, content):
        key = f"tenants/{tenant_id}/{env}/media_v2/{asset_id}/{filename}"
        self.uploads.append({"tenant": tenant_id, "env": env, "asset_id": asset_id, "key": key, "body": content})
        return f"s3://test-bucket/{key}"


def _reset_media_service(storage=None):
    repo = InMemoryMediaRepository()
    storage = storage or StubS3Storage()
    set_media_service(MediaService(repo=repo, storage=storage))
    return storage


def _auth_token(tenant_id: str = "t_test", user_id: str = "u1"):
    svc = default_jwt_service()
    claims = {
        "sub": user_id,
        "email": f"{user_id}@example.com",
        "tenant_ids": [tenant_id],
        "default_tenant_id": tenant_id,
        "role_map": {tenant_id: "member"},
    }
    return svc.issue_token(claims)


MEDIA_PROJECT_ID = "p_media"


def _auth_headers(tenant_id: str = "t_test", user_id: str = "u1", mode: str = "lab"):
    return {
        "Authorization": f"Bearer {_auth_token(tenant_id=tenant_id, user_id=user_id)}",
        "X-Tenant-Id": tenant_id,
        "X-Project-Id": MEDIA_PROJECT_ID,
        "X-Mode": mode,
    }


def _assert_error_envelope(resp, expected_code: str | None = None, expected_status: int | None = None):
    assert resp.status_code == expected_status if expected_status else resp.status_code >= 400
    payload = resp.json()
    assert isinstance(payload, dict)
    error = payload.get("error")
    assert isinstance(error, dict)
    if expected_code:
        assert error.get("code") == expected_code
    if expected_status:
        assert error.get("http_status") == expected_status
    return error


def setup_module(_module):
    os.environ.setdefault("AUTH_JWT_SIGNING", "media-secret")
    os.environ.setdefault("MEDIA_V2_ALLOW_LOCAL_STORAGE", "1")
    os.environ.setdefault("ENV", "dev")
    _reset_media_service()
    identity_repo = InMemoryIdentityRepository()
    tenants = ["t_test", "t_tenant_a", "t_tenant_b"]
    for tenant in tenants:
        surface = Surface(tenant_id=tenant, name=f"default-{tenant}")
        identity_repo.create_surface(surface)
        app_record = App(tenant_id=tenant, name=f"default-app-{tenant}")
        identity_repo.create_app(app_record)
    set_identity_repo(identity_repo)
    global _client
    app = FastAPI()
    app.include_router(media_router)
    register_media_error_handlers(app)
    _client = TestClient(app, raise_server_exceptions=False)


def test_media_v2_upload_and_artifact():
    storage = _reset_media_service(StubS3Storage())
    client = _client
    headers = _auth_headers()
    files = {"file": ("audio.wav", BytesIO(b"12345"), "audio/wav")}
    resp = client.post(
        "/media-v2/assets",
        files=files,
        data={"kind": "audio"},
        headers=headers,
    )
    assert resp.status_code == 200
    asset = resp.json()
    asset_id = asset["id"]
    assert asset["source_uri"].startswith("s3://test-bucket/tenants/t_test/dev/media_v2/")

    resp2 = client.post(
        f"/media-v2/assets/{asset_id}/artifacts",
        data={"kind": "audio_segment", "uri": "/tmp/seg1.mp3", "start_ms": 0},
        headers=headers,
    )
    assert resp2.status_code == 200
    artifact_id = resp2.json()["id"]

    resp3 = client.get(f"/media-v2/assets/{asset_id}", headers=headers)
    assert resp3.status_code == 200
    body = resp3.json()
    assert body["asset"]["id"] == asset_id
    assert body["artifacts"][0]["id"] == artifact_id

    resp4 = client.get("/media-v2/assets", params={"tenant_id": "t_test"}, headers=headers)
    assert resp4.status_code == 200
    assert len(resp4.json()) >= 1
    assert storage.uploads[0]["key"].startswith("tenants/t_test/dev/media_v2/")


def test_tenant_isolation_and_prefixing():
    storage = _reset_media_service(StubS3Storage())
    client = _client
    headers_a = _auth_headers(tenant_id="t_tenant_a")
    files = {"file": ("tiny.bin", BytesIO(b"abc"), "application/octet-stream")}
    resp = client.post("/media-v2/assets", files=files, data={}, headers=headers_a)
    assert resp.status_code == 200
    asset = resp.json()
    assert asset["tenant_id"] == "t_tenant_a"
    assert asset["source_uri"].startswith("s3://test-bucket/tenants/t_tenant_a/dev/media_v2/")

    # Authenticate as Tenant B to verify we see nothing
    headers_b = _auth_headers(tenant_id="t_tenant_b")
    resp_list_b = client.get("/media-v2/assets", params={"tenant_id": "t_tenant_b", "env": "dev"}, headers=headers_b)
    assert resp_list_b.status_code == 200
    assert resp_list_b.json() == []

    assert storage.uploads
    assert storage.uploads[0]["key"].startswith("tenants/t_tenant_a/dev/media_v2/")


def test_missing_headers_rejected():
    client = _client
    files = {"file": ("audio.wav", BytesIO(b"12345"), "audio/wav")}
    headers = {
        "X-Tenant-Id": "t_test",
        "X-Project-Id": MEDIA_PROJECT_ID,
        "X-Mode": "lab",
    }
    resp = client.post("/media-v2/assets", files=files, data={"kind": "audio"}, headers=headers)
    assert _assert_error_envelope(resp, expected_status=401)


def test_missing_project_id_rejected():
    client = _client
    files = {"file": ("audio.wav", BytesIO(b"12345"), "audio/wav")}
    headers = dict(_auth_headers())
    headers.pop("X-Project-Id", None)
    resp = client.post("/media-v2/assets", files=files, data={"kind": "audio"}, headers=headers)
    assert _assert_error_envelope(resp, expected_status=400)


def test_cross_tenant_rejected():
    client = _client
    headers = _auth_headers(tenant_id="t_bad")
    headers["X-Tenant-Id"] = "t_test"
    files = {"file": ("audio.wav", BytesIO(b"data"), "audio/wav")}
    resp = client.post("/media-v2/assets", files=files, data={"kind": "audio"}, headers=headers)
    assert _assert_error_envelope(resp, expected_status=403)


def test_remote_payload_tenant_mismatch():
    client = _client
    headers = _auth_headers()
    payload = {
        "tenant_id": "t_other",
        "env": "dev",
        "user_id": "u1",
        "kind": "image",
        "source_uri": "gs://bucket/video.mp4",
    }
    resp = client.post("/media-v2/assets", json=payload, headers=headers)
    assert _assert_error_envelope(resp, expected_status=400)


def test_video_region_summary_validation():
    from engines.media_v2.service import MediaService, InMemoryMediaRepository, LocalMediaStorage
    from engines.media_v2.models import MediaUploadRequest, ArtifactCreateRequest
    
    svc = MediaService(repo=InMemoryMediaRepository(), storage=LocalMediaStorage())
    # Create parent asset
    asset_req = MediaUploadRequest(tenant_id="t1", env="dev", kind="video", source_uri="s3://vid.mp4")
    asset = svc.register_upload(asset_req, "vid.mp4", b"data")
    
    # Case 1: Missing metadata should be populated with defaults
    art_default = svc.register_artifact(ArtifactCreateRequest(
        tenant_id="t1",
        env="dev",
        parent_asset_id=asset.id,
        kind="video_region_summary",
        uri="gs://sum.json",
        meta={},
    ))
    assert art_default.meta["backend_version"].endswith("_unknown")
    assert art_default.meta["model_used"].endswith("_unknown")
    assert art_default.meta["cache_key"].endswith("_auto_cache")
    assert art_default.meta["duration_ms"] == 0

    # Case 2: Success - Full meta
    art = svc.register_artifact(ArtifactCreateRequest(
        tenant_id="t1", 
        env="dev", 
        parent_asset_id=asset.id, 
        kind="video_region_summary", 
        uri="gs://sum.json",
        meta={
            "backend_version": "v1",
            "model_used": "v1",
            "cache_key": "k1"
        }
    ))
    assert art.kind == "video_region_summary"
    assert art.meta["backend_version"] == "v1"


def test_saas_missing_raw_bucket_rejected(monkeypatch):
    _reset_media_service(StubS3Storage())
    client = _client
    monkeypatch.delenv("MEDIA_V2_ALLOW_LOCAL_STORAGE", raising=False)
    monkeypatch.delenv("RAW_BUCKET", raising=False)
    monkeypatch.delenv("GCP_PROJECT", raising=False)
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    monkeypatch.setenv("ENV", "prod")
    headers = _auth_headers(mode="saas")
    files = {"file": ("asset.bin", BytesIO(b"bytes"), "application/octet-stream")}
    resp = client.post("/media-v2/assets", files=files, data={}, headers=headers)
    error = _assert_error_envelope(resp, expected_code="media_v2.raw_bucket_missing", expected_status=500)
    assert error["resource_kind"] == "media_v2"


def test_register_vector_scene_artifact_meta():
    # Use service directly
    from engines.media_v2.service import MediaService, InMemoryMediaRepository, LocalMediaStorage
    svc = MediaService(repo=InMemoryMediaRepository(), storage=LocalMediaStorage())
    from engines.media_v2.models import MediaUploadRequest, ArtifactCreateRequest
    asset = svc.register_upload(MediaUploadRequest(tenant_id="t", env="test", kind="image", source_uri="pending"), "f.png", b"data")
    art_req = ArtifactCreateRequest(tenant_id="t", env="test", parent_asset_id=asset.id, kind="vector_scene", uri=asset.source_uri, meta={"layout_hash": "abc"})
    art = svc.register_artifact(art_req)
    assert art.kind == "vector_scene"
    assert art.meta.get("layout_hash") == "abc"


def test_artifact_meta_records_pipeline_hash_and_backend(monkeypatch):
    monkeypatch.setenv("MEDIA_V2_BACKEND_VERSION", "media_v2_test_v1")
    from engines.media_v2.service import MediaService, InMemoryMediaRepository, LocalMediaStorage
    from engines.media_v2.models import MediaUploadRequest, ArtifactCreateRequest

    svc = MediaService(repo=InMemoryMediaRepository(), storage=LocalMediaStorage())
    asset = svc.register_upload(MediaUploadRequest(tenant_id="t_meta", env="test", kind="audio", source_uri="s3://bucket/asset"), "file.bin", b"data")

    def build_request():
        return ArtifactCreateRequest(
            tenant_id="t_meta",
            env="test",
            parent_asset_id=asset.id,
            kind="audio_segment",
            uri="s3://bucket/segment",
            meta={"note": "meta"},
        )

    art_a = svc.register_artifact(build_request())
    art_b = svc.register_artifact(build_request())
    assert art_a.meta["pipeline_hash"] == art_b.meta["pipeline_hash"]
    assert art_a.meta["backend_version"] == "media_v2_test_v1"


def test_get_requires_auth():
    """Verify that GET endpoints require authentication."""
    _reset_media_service()
    client = _client
    
    # Provide context headers but no Auth header to test 401
    ctx_headers = {
        "X-Tenant-Id": "t_test",
        "X-Project-Id": MEDIA_PROJECT_ID,
    }
    ctx_headers["X-Mode"] = "lab"
    
    # 1. Test GET /assets/{id} without auth
    resp_get = client.get("/media-v2/assets/any-id", headers=ctx_headers)
    _assert_error_envelope(resp_get, expected_status=401)

    # 2. Test GET /assets (list) without auth
    resp_list = client.get("/media-v2/assets", params={"tenant_id": "t_test"}, headers=ctx_headers)
    _assert_error_envelope(resp_list, expected_status=401)

    # 3. Test GET /assets (list) with valid auth but mismatched tenant
    headers = _auth_headers(tenant_id="t_test", user_id="u1")
    # Requesting t_other not in token
    resp_mismatch = client.get("/media-v2/assets", params={"tenant_id": "t_other"}, headers=headers)
    _assert_error_envelope(resp_mismatch, expected_status=403)

    # 4. Success case for list
    resp_ok = client.get("/media-v2/assets", params={"tenant_id": "t_test"}, headers=headers)
    assert resp_ok.status_code == 200
