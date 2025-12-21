import os
from io import BytesIO

from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.identity.jwt_service import default_jwt_service
from engines.media_v2.routes import router as media_router
from engines.media_v2.service import InMemoryMediaRepository, MediaService, set_media_service

_client: TestClient | None = None


class StubS3Storage:
    def __init__(self):
        self.uploads = []

    def upload_bytes(self, tenant_id, env, asset_id, filename, content):
        key = f"tenants/{tenant_id}/{env}/media_v2/{asset_id}/{filename}"
        self.uploads.append({"tenant": tenant_id, "env": env, "asset_id": asset_id, "key": key, "body": content})
        return f"s3://test-bucket/{key}"


class FailingStorage:
    def upload_bytes(self, tenant_id, env, asset_id, filename, content):
        raise RuntimeError("boom")


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


def _auth_headers(tenant_id: str = "t_test", env: str = "dev", user_id: str = "u1"):
    return {
        "Authorization": f"Bearer {_auth_token(tenant_id=tenant_id, user_id=user_id)}",
        "X-Tenant-Id": tenant_id,
        "X-Env": env,
    }


def setup_module(_module):
    os.environ.setdefault("AUTH_JWT_SIGNING", "media-secret")
    _reset_media_service()
    global _client
    app = FastAPI()
    app.include_router(media_router)
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

    resp3 = client.get(f"/media-v2/assets/{asset_id}")
    assert resp3.status_code == 200
    body = resp3.json()
    assert body["asset"]["id"] == asset_id
    assert body["artifacts"][0]["id"] == artifact_id

    resp4 = client.get("/media-v2/assets", params={"tenant_id": "t_test"})
    assert resp4.status_code == 200
    assert len(resp4.json()) >= 1
    assert storage.uploads[0]["key"].startswith("tenants/t_test/dev/media_v2/")


def test_tenant_isolation_and_prefixing():
    storage = _reset_media_service(StubS3Storage())
    client = _client
    headers = _auth_headers(tenant_id="t_tenant_a")
    files = {"file": ("tiny.bin", BytesIO(b"abc"), "application/octet-stream")}
    resp = client.post("/media-v2/assets", files=files, data={}, headers=headers)
    assert resp.status_code == 200
    asset = resp.json()
    assert asset["tenant_id"] == "t_tenant_a"
    assert asset["source_uri"].startswith("s3://test-bucket/tenants/t_tenant_a/dev/media_v2/")

    resp_list_b = client.get("/media-v2/assets", params={"tenant_id": "t_tenant_b"})
    assert resp_list_b.status_code == 200
    assert resp_list_b.json() == []

    assert storage.uploads
    assert storage.uploads[0]["key"].startswith("tenants/t_tenant_a/dev/media_v2/")


def test_missing_headers_rejected():
    client = _client
    files = {"file": ("audio.wav", BytesIO(b"12345"), "audio/wav")}
    headers = {"X-Tenant-Id": "t_test", "X-Env": "dev"}
    resp = client.post("/media-v2/assets", files=files, data={"kind": "audio"}, headers=headers)
    assert resp.status_code == 401


def test_cross_tenant_rejected():
    client = _client
    headers = _auth_headers(tenant_id="t_bad")
    headers["X-Tenant-Id"] = "t_test"
    files = {"file": ("audio.wav", BytesIO(b"data"), "audio/wav")}
    resp = client.post("/media-v2/assets", files=files, data={"kind": "audio"}, headers=headers)
    assert resp.status_code == 403


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
    assert resp.status_code == 400


def test_prod_mode_rejects_local_fallback():
    _reset_media_service(FailingStorage())
    client = _client
    headers = _auth_headers(env="prod")
    files = {"file": ("asset.bin", BytesIO(b"bytes"), "application/octet-stream")}
    resp = client.post("/media-v2/assets", files=files, data={}, headers=headers)
    assert resp.status_code == 500


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


def test_get_requires_auth():
    """Verify that GET endpoints require authentication."""
    _reset_media_service()
    client = _client
    
    # Provide context headers but no Auth header to test 401
    ctx_headers = {"X-Tenant-Id": "t_test", "X-Env": "dev"}
    
    # 1. Test GET /assets/{id} without auth
    resp_get = client.get("/media-v2/assets/any-id", headers=ctx_headers)
    assert resp_get.status_code == 401

    # 2. Test GET /assets (list) without auth
    resp_list = client.get("/media-v2/assets", params={"tenant_id": "t_test"}, headers=ctx_headers)
    assert resp_list.status_code == 401

    # 3. Test GET /assets (list) with valid auth but mismatched tenant
    headers = _auth_headers(tenant_id="t_test", user_id="u1")
    # Requesting t_other not in token
    resp_mismatch = client.get("/media-v2/assets", params={"tenant_id": "t_other"}, headers=headers)
    assert resp_mismatch.status_code == 403

    # 4. Success case for list
    resp_ok = client.get("/media-v2/assets", params={"tenant_id": "t_test"}, headers=headers)
    assert resp_ok.status_code == 200
