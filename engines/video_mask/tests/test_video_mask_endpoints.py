import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.media_v2.models import MediaUploadRequest
from engines.media_v2.service import InMemoryMediaRepository, MediaService, set_media_service
from engines.video_mask.service import MaskService, DummyMaskBackend, set_mask_service


def setup_module(_module):
    set_media_service(MediaService(repo=InMemoryMediaRepository()))
    set_mask_service(MaskService(backend=DummyMaskBackend()))


def test_create_mask_and_get():
    media_service = MediaService(repo=InMemoryMediaRepository())
    set_media_service(media_service)
    set_mask_service(MaskService(backend=DummyMaskBackend()))
    asset_path = Path(tempfile.mkdtemp()) / "video.mp4"
    asset_path.write_bytes(b"123")
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="video", source_uri=str(asset_path))
    )

    client = TestClient(create_app())
    resp = client.post(
        "/video/masks/auto",
        json={
            "tenant_id": "t_test",
            "env": "dev",
            "user_id": "u1",
            "source_asset_id": asset.id,
            "prompt": {"prompt_type": "point", "x": 0.5, "y": 0.5},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["artifact_id"]

    resp2 = client.get(f"/video/masks/{body['artifact_id']}")
    assert resp2.status_code == 200
