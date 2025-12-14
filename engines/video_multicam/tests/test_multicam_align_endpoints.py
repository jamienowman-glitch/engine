from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from engines.video_multicam.routes import router
from engines.video_multicam.service import MultiCamService, get_multicam_service, StubAlignBackend
from engines.video_multicam.models import MultiCamSession, MultiCamTrackSpec
from engines.media_v2.models import MediaAsset

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_align_endpoint():
    # Service Mock
    # We need a service that has a session already in its repo
    mock_media = MagicMock()
    mock_media.get_asset.return_value = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", source_uri="gs://foo")
    
    service = MultiCamService(media_service=mock_media, align_backend=StubAlignBackend())
    session = MultiCamSession(
        tenant_id="t1", env="dev", name="Align Remote", 
        tracks=[{"asset_id": "a1", "role": "primary"}]
    )
    service.repo.create(session)
    
    app.dependency_overrides[get_multicam_service] = lambda: service

    resp = client.post(f"/video/multicam/sessions/{session.id}/align", json={
        "tenant_id": "t1",
        "env": "dev",
        "session_id": session.id
    })
    assert resp.status_code == 200
    res = resp.json()
    assert res["session_id"] == session.id
    assert "a1" in res["offsets_ms"]
