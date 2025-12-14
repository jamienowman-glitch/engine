from io import BytesIO

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.media_v2.service import InMemoryMediaRepository, MediaService, set_media_service


class StubGcs:
    def __init__(self):
        self.uploads = []

    def upload_raw_media(self, tenant_id, path, content):
        self.uploads.append((tenant_id, path, content))
        return f"/tmp/{tenant_id}/{path}"


def setup_module(_module):
    repo = InMemoryMediaRepository()
    set_media_service(MediaService(repo=repo, gcs=StubGcs()))


def test_media_v2_upload_and_artifact():
    client = TestClient(create_app())
    files = {"file": ("audio.wav", BytesIO(b"12345"), "audio/wav")}
    resp = client.post(
        "/media-v2/assets",
        files=files,
        data={"tenant_id": "t_test", "env": "dev", "user_id": "u1", "kind": "audio"},
    )
    assert resp.status_code == 200
    asset = resp.json()
    asset_id = asset["id"]

    # create artifact
    resp2 = client.post(
        f"/media-v2/assets/{asset_id}/artifacts",
        data={"tenant_id": "t_test", "env": "dev", "kind": "audio_segment", "uri": "/tmp/seg1.mp3", "start_ms": 0},
    )
    assert resp2.status_code == 200
    artifact_id = resp2.json()["id"]

    # fetch asset with artifacts
    resp3 = client.get(f"/media-v2/assets/{asset_id}")
    assert resp3.status_code == 200
    body = resp3.json()
    assert body["asset"]["id"] == asset_id
    assert body["artifacts"][0]["id"] == artifact_id

    # list assets
    resp4 = client.get("/media-v2/assets", params={"tenant_id": "t_test"})
    assert resp4.status_code == 200
    assert len(resp4.json()) >= 1
