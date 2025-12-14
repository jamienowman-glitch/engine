from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from engines.video_multicam.routes import router
from engines.video_multicam.service import MultiCamService, get_multicam_service
from engines.video_multicam.models import MultiCamSession, MultiCamTrackSpec
from engines.media_v2.models import MediaAsset

app = MagicMock() # Placeholder if needed, but we can test router or build small app
from fastapi import FastAPI
app = FastAPI()
app.include_router(router)

client = TestClient(app)

def mock_get_service():
    mock_media = MagicMock()
    mock_media.get_asset.return_value = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", source_uri="gs://foo")
    return MultiCamService(media_service=mock_media)

app.dependency_overrides[get_multicam_service] = mock_get_service

def test_session_endpoints():
    # POST
    resp = client.post("/video/multicam/sessions", json={
        "tenant_id": "t1",
        "env": "dev",
        "name": "Endpoint Session",
        "tracks": [{"asset_id": "a1", "role": "primary"}]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Endpoint Session"
    session_id = data["id"]
    
    # GET ID
    resp = client.get(f"/video/multicam/sessions/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == session_id
    
    # GET List
    resp = client.get("/video/multicam/sessions", params={"tenant_id": "t1"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
