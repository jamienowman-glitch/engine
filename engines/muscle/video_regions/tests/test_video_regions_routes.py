from fastapi.testclient import TestClient
from fastapi import FastAPI
from engines.video_regions.routes import router
from engines.video_regions.service import get_video_regions_service, VideoRegionsService
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import get_auth_context
from engines.identity.jwt_service import AuthContext
from engines.media_v2.models import MediaAsset, DerivedArtifact
from unittest.mock import MagicMock, patch

def _video_regions_context() -> RequestContext:
    return RequestContext(tenant_id="t_test", env="dev", project_id="p_video_regions")


def _video_regions_auth() -> AuthContext:
    return AuthContext(
        user_id="regions_user",
        email="regions@example.com",
        tenant_ids=["t_test"],
        default_tenant_id="t_test",
        role_map={"t_test": "owner"},
    )


app = FastAPI()
app.include_router(router)
app.dependency_overrides[get_request_context] = _video_regions_context
app.dependency_overrides[get_auth_context] = _video_regions_auth
client = TestClient(app)

def test_routes_analyze():
    mock_media = MagicMock()
    mock_media.get_asset.return_value = MediaAsset(id="a1", tenant_id="t_test", env="dev", kind="video", source_uri="")
    # Minimal mock for artifact return
    mock_media.register_artifact.return_value = DerivedArtifact(id="art_sum", parent_asset_id="a1", tenant_id="t1", env="dev", kind="video_region_summary", uri="gs://fake.json")
    
    service = VideoRegionsService(media_service=mock_media)
    headers = {"X-Tenant-Id": "t_test", "X-Env": "dev"}
    with patch("engines.video_regions.routes.get_video_regions_service", return_value=service):
        resp = client.post("/video/regions/analyze", json={
            "tenant_id": "t_test", "env": "dev", "asset_id": "a1", "include_regions": ["face"]
        }, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary_artifact_id"] == "art_sum"
