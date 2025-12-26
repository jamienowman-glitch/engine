from fastapi.testclient import TestClient
from fastapi import FastAPI
from engines.video_360.routes import router
from engines.video_360.models import VirtualCameraPath
from engines.video_360.service import get_video_360_service, Video360Service
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import get_auth_context
from engines.identity.jwt_service import AuthContext
from engines.media_v2.models import MediaAsset
from unittest.mock import MagicMock, patch

def _mock_video_360_context() -> RequestContext:
    return RequestContext(tenant_id="t_test", env="dev", project_id="p_video_360")


def _mock_video_360_auth() -> AuthContext:
    return AuthContext(
        user_id="v360_user",
        email="v360@example.com",
        tenant_ids=["t_test"],
        default_tenant_id="t_test",
        role_map={"t_test": "owner"},
    )


app = FastAPI()
app.include_router(router)
app.dependency_overrides[get_request_context] = _mock_video_360_context
app.dependency_overrides[get_auth_context] = _mock_video_360_auth
client = TestClient(app)

def test_routes_crud():
    # Setup
    service = Video360Service(media_service=MagicMock())
    # app.dependency_overrides[get_video_360_service] = lambda: service
    # Use patch because route calls function directly
    with patch("engines.video_360.routes.get_video_360_service", return_value=service):
        # Create
        resp = client.post("/video/360/camera-paths", json={
            "tenant_id": "t_test", "env": "dev", "asset_id": "a1", "name": "Path 1",
            "keyframes": [{"time_ms": 0, "yaw": 0}]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Path 1"
        path_id = data["id"]
        
        # Get
        resp = client.get(f"/video/360/camera-paths/{path_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == path_id
        
        # List
        resp = client.get("/video/360/camera-paths", params={"tenant_id": "t_test"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

def test_routes_render():
    # Setup Mock Media Service
    mock_media = MagicMock()
    mock_media.get_asset.return_value = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", is_360=True, source_uri="gs://test/360.mp4")
    # Mock register_remote to return a dummy asset
    mock_media.register_remote.return_value = MediaAsset(id="new_asset", tenant_id="t1", env="dev", kind="video", source_uri="gs://test/out.mp4")
    # Mock register_artifact
    mock_artifact = MagicMock()
    mock_artifact.id = "art_1"
    mock_artifact.meta = {"backend_version": "v1"}
    mock_media.register_artifact.return_value = mock_artifact
    
    service = Video360Service(media_service=mock_media)
    # app.dependency_overrides[get_video_360_service] = lambda: service

    # Mock subprocess.run to avoid actual ffmpeg execution
    with patch("engines.video_360.routes.get_video_360_service", return_value=service), \
         patch("engines.video_360.service.subprocess.run") as mock_run:
        
        # Render request with inline path
        resp = client.post("/video/360/render", json={
            "tenant_id": "t_test", "env": "dev", "asset_id": "a1",
            "path": {
                "tenant_id": "t_test", "env": "dev", "asset_id": "a1",
                "keyframes": [{"time_ms": 0, "yaw": 0}]
            }
        })
        
        if resp.status_code != 200:
            print(f"Render failed: {resp.json()}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["asset_id"] == "new_asset"
