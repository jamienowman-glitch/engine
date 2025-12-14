from fastapi.testclient import TestClient
from fastapi import FastAPI
from engines.video_regions.routes import router
from engines.video_regions.service import get_video_regions_service, VideoRegionsService
from engines.media_v2.models import MediaAsset, DerivedArtifact
from unittest.mock import MagicMock, patch

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_routes_analyze():
    mock_media = MagicMock()
    mock_media.get_asset.return_value = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", source_uri="")
    # Minimal mock for artifact return
    mock_media.register_artifact.return_value = DerivedArtifact(id="art_sum", parent_asset_id="a1", tenant_id="t1", env="dev", kind="video_region_summary", uri="gs://fake.json")
    
    service = VideoRegionsService(media_service=mock_media)
    
    with patch("engines.video_regions.routes.get_video_regions_service", return_value=service):
        resp = client.post("/video/regions/analyze", json={
            "tenant_id": "t1", "env": "dev", "asset_id": "a1", "include_regions": ["face"]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary_artifact_id"] == "art_sum"
