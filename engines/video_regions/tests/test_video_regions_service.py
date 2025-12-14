from unittest.mock import MagicMock
from engines.media_v2.models import MediaAsset, DerivedArtifact
from engines.video_regions.service import VideoRegionsService
from engines.video_regions.models import AnalyzeRegionsRequest

def test_analyze_regions_stub():
    # Mock Media Service
    mock_media = MagicMock()
    mock_media.get_asset.return_value = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", duration_ms=5000, source_uri="")
    
    # Mock registration
    def register_artifact(req):
        return DerivedArtifact(
            id=f"art_{req.kind}_{len(mock_media.register_artifact.call_args_list)}",
            parent_asset_id=req.parent_asset_id,
            tenant_id=req.tenant_id,
            env=req.env,
            kind=req.kind,
            uri=req.uri,
            meta=req.meta
        )
    mock_media.register_artifact.side_effect = register_artifact
    
    service = VideoRegionsService(media_service=mock_media)
    
    req = AnalyzeRegionsRequest(
        tenant_id="t1", env="dev", asset_id="a1", include_regions=["face", "teeth"]
    )
    result = service.analyze_regions(req)
    
    assert result.summary_artifact_id
    assert result.summary.asset_id == "a1"
    
    # Check entries
    entries = result.summary.entries
    assert len(entries) == 2 # face, teeth
    assert entries[0].region == "face"
    assert entries[1].region == "teeth"
    assert entries[0].mask_artifact_id.startswith("art_mask")
    
    # Verify artifact registration calls
    # 1 mask, 1 summary
    assert mock_media.register_artifact.call_count == 2 
    kinds = [c.args[0].kind for c in mock_media.register_artifact.call_args_list]
    assert "mask" in kinds
    assert "video_region_summary" in kinds

def test_get_analysis():
    # Integrated test with file read
    mock_media = MagicMock()
    service = VideoRegionsService(media_service=mock_media)
    
    # Manually create a request to gen a file
    mock_media.get_asset.return_value = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", source_uri="")
    # For this test we need register_artifact to behave reasonably so we can capture URI
    created_uris = {}
    def register_artifact(req):
        created_uris[req.kind] = req.uri
        return DerivedArtifact(id="art_1", parent_asset_id="a1", tenant_id="t1", env="dev", kind=req.kind, uri=req.uri)
    mock_media.register_artifact.side_effect = register_artifact
    
    req = AnalyzeRegionsRequest(tenant_id="t1", env="dev", asset_id="a1")
    result = service.analyze_regions(req)
    
    # Reset mock and setup get
    mock_media.get_artifact.return_value = DerivedArtifact(
        id="art_summary", parent_asset_id="a1", tenant_id="t1", env="dev", 
        kind="video_region_summary", uri=created_uris["video_region_summary"]
    )
    
    # Test Get
    fetched = service.get_analysis("art_summary")
    assert fetched.asset_id == "a1"
    assert len(fetched.entries) > 0
