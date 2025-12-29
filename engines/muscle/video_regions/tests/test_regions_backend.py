import os
from unittest.mock import MagicMock, patch
from engines.video_regions.service import VideoRegionsService
from engines.video_regions.models import AnalyzeRegionsRequest
from engines.media_v2.models import MediaAsset, Artifact

def test_stub_backend():
    # Default behavior
    mock_media = MagicMock()
    mock_asset = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", duration_ms=10000, source_uri="/tmp/fake.mp4")
    mock_media.get_asset.return_value = mock_asset
    
    # Mock register artifact to return something with ID
    def fake_register(req):
        return Artifact(id="art_" + req.kind, tenant_id=req.tenant_id, env=req.env, kind=req.kind, parent_asset_id=req.parent_asset_id, uri=req.uri)
    mock_media.register_artifact.side_effect = fake_register
    
    service = VideoRegionsService(media_service=mock_media)
    
    req = AnalyzeRegionsRequest(tenant_id="t1", env="dev", asset_id="a1")
    result = service.analyze_regions(req)
    
    summary = result.summary
    assert summary.meta["backend_version"] == "video_regions_stub_v1"
    assert len(summary.entries) > 0

def test_cpu_face_backend():
    # ENV override
    with patch.dict(os.environ, {"VIDEO_REGION_BACKEND": "cpu_face"}):
        mock_media = MagicMock()
        mock_asset = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", duration_ms=10000, source_uri="/tmp/fake.mp4")
        mock_media.get_asset.return_value = mock_asset
        
        def fake_register(req):
             return Artifact(id="art_" + req.kind, tenant_id=req.tenant_id, env=req.env, kind=req.kind, parent_asset_id=req.parent_asset_id, uri=req.uri)
        mock_media.register_artifact.side_effect = fake_register

        service = VideoRegionsService(media_service=mock_media)
        # Should have loaded cpu backend
        
        req = AnalyzeRegionsRequest(tenant_id="t1", env="dev", asset_id="a1", include_regions=["face"])
        result = service.analyze_regions(req)
        
        summary = result.summary
        assert summary.meta["backend_version"] == "video_regions_cpu_face_v1_stub"
        
        # Verify creating circle mask logic runs (we can't easily check the image content without reading file, 
        # but we check uniqueness of backend output)
        face_entries = [e for e in summary.entries if e.region == "face"]
        assert len(face_entries) > 0
