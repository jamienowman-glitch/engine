import os
from unittest.mock import MagicMock, patch

from engines.media_v2.models import MediaAsset, DerivedArtifact
from engines.media_v2.models import MediaAsset, DerivedArtifact
from engines.video_regions.models import AnalyzeRegionsRequest, RegionAnalysisSummary, RegionMaskEntry, AnalyzeRegionsResult
from engines.video_regions.service import VideoRegionsService


def test_analyze_regions_stub():
    mock_media = MagicMock()
    mock_media.get_asset.return_value = MediaAsset(
        id="a1", tenant_id="t1", env="dev", kind="video", duration_ms=5000, source_uri=""
    )

    def register_artifact(req):
        return DerivedArtifact(
            id=f"art_{req.kind}_{len(mock_media.register_artifact.call_args_list)}",
            parent_asset_id=req.parent_asset_id,
            tenant_id=req.tenant_id,
            env=req.env,
            kind=req.kind,
            uri=req.uri,
            meta=req.meta,
        )

    mock_media.register_artifact.side_effect = register_artifact

    with patch.dict(os.environ, {"VIDEO_REGION_BACKEND": "stub"}):
        service = VideoRegionsService(media_service=mock_media)
        req = AnalyzeRegionsRequest(
            tenant_id="t1", env="dev", asset_id="a1", include_regions=["face", "teeth"]
        )
        result = service.analyze_regions(req)

    assert result.summary_artifact_id
    assert result.summary.asset_id == "a1"
    entries = result.summary.entries
    assert len(entries) == 2
    assert entries[0].region == "face"
    assert entries[1].region == "teeth"
    assert entries[0].mask_artifact_id.startswith("art_")
    assert mock_media.register_artifact.call_count == 2
    kinds = [c.args[0].kind for c in mock_media.register_artifact.call_args_list]
    assert "mask" in kinds
    assert "video_region_summary" in kinds


def test_get_analysis():
    mock_media = MagicMock()
    mock_media.get_asset.return_value = MediaAsset(
        id="a1", tenant_id="t1", env="dev", kind="video", source_uri=""
    )
    created_uris: dict[str, str] = {}

    def register_artifact(req):
        created_uris[req.kind] = req.uri
        return DerivedArtifact(
            id="art_1",
            parent_asset_id="a1",
            tenant_id="t1",
            env="dev",
            kind=req.kind,
            uri=req.uri,
            meta=req.meta,
        )

    mock_media.register_artifact.side_effect = register_artifact
    with patch.dict(os.environ, {"VIDEO_REGION_BACKEND": "stub"}):
        service = VideoRegionsService(media_service=mock_media)
        req = AnalyzeRegionsRequest(tenant_id="t1", env="dev", asset_id="a1")
        service.analyze_regions(req)

    mock_media.get_artifact.return_value = DerivedArtifact(
        id="art_summary",
        parent_asset_id="a1",
        tenant_id="t1",
        env="dev",
        kind="video_region_summary",
        uri=created_uris["video_region_summary"],
    )
    fetched = service.get_analysis("art_summary")
    assert fetched is not None
    assert fetched.asset_id == "a1"
    assert len(fetched.entries) > 0


def test_analyze_regions_cache_reused():
    """Verify that if a valid cached artifact exists, the backend is not called again."""
    mock_media = MagicMock()
    asset = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", duration_ms=5000, source_uri="fake.mp4")
    mock_media.get_asset.return_value = asset

    # Setup specific existing artifact that matches the expected cache key
    # The cache key for stub + face/teeth is: "a1|video_regions_stub_v1|face,teeth"
    expected_cache_key = "a1|video_regions_stub_v1|face,teeth"
    
    mock_artifact = DerivedArtifact(
        id="art_existing_summary",
        parent_asset_id="a1",
        tenant_id="t1",
        env="dev",
        kind="video_region_summary",
        uri="gs://bucket/existing.json",
        meta={
            "cache_key": expected_cache_key,
            "backend_version": "video_regions_stub_v1"
        }
    )
    mock_media.list_artifacts_for_asset.return_value = [mock_artifact]

    # Mock loading the summary from URI
    existing_summary = RegionAnalysisSummary(
        tenant_id="t1",
        env="dev",
        asset_id="a1",
        entries=[
            RegionMaskEntry(time_ms=0, region="face", mask_artifact_id="m1")
        ],
        meta={"cache_key": expected_cache_key, "backend_version": "video_regions_stub_v1"}
    )
    
    service = VideoRegionsService(media_service=mock_media)
    # Patch the internal loader to avoid FileNotFoundError
    with patch.object(service, "_load_summary_from_uri", return_value=existing_summary):
        # Patch backend to ensure it's NOT called
        service.backend = MagicMock()
        service.backend.backend_version = "video_regions_stub_v1" # CRITICAL: must match cache_key
        service.stub_backend = MagicMock()
        
        req = AnalyzeRegionsRequest(
            tenant_id="t1", env="dev", asset_id="a1", include_regions=["face", "teeth"]
        )
        result = service.analyze_regions(req)
        
        assert result.summary_artifact_id == "art_existing_summary"
        service.backend.analyze.assert_not_called()
        service.stub_backend.analyze.assert_not_called()


def test_analyze_regions_dependency_missing_fallback():
    """Verify fallback to stub when MissingDependencyError occurs."""
    mock_media = MagicMock()
    mock_media.get_asset.return_value = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", source_uri="fake.mp4")
    
    # We want to use a real/opencv backend logic that RAISES MissingDependencyError
    # So we force env var to 'opencv' but ensure it raises
    with patch.dict(os.environ, {"VIDEO_REGION_BACKEND": "opencv"}):
        service = VideoRegionsService(media_service=mock_media)
        
        # Mock the backend to raise
        service.backend = MagicMock()
        service.backend.backend_version = "video_regions_opencv_v1" # set version
        from engines.video_regions.backend import MissingDependencyError
        service.backend.analyze.side_effect = MissingDependencyError("No OpenCV")
        
        # Mock stub backend to return a result
        service.stub_backend = MagicMock()
        stub_summary = RegionAnalysisSummary(
             tenant_id="t1", env="dev", asset_id="a1", entries=[],
             meta={"backend_version": "video_regions_stub_v1"}
        )
        service.stub_backend.analyze.return_value = AnalyzeRegionsResult(
            summary_artifact_id="stub_art", summary=stub_summary
        )

        req = AnalyzeRegionsRequest(tenant_id="t1", env="dev", asset_id="a1")
        result = service.analyze_regions(req)
        
        service.backend.analyze.assert_called_once()
        service.stub_backend.analyze.assert_called_once()  # Fallback happened
        assert result.summary_artifact_id == "stub_art"
        assert result.summary.meta["backend_version"] == "video_regions_stub_v1"



def test_tenant_env_validation_failures():
    mock_media = MagicMock()
    service = VideoRegionsService(media_service=mock_media)
    
    # Missing tenant
    try:
        service.analyze_regions(AnalyzeRegionsRequest(tenant_id="", env="dev", asset_id="a1"))
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "valid tenant_id" in str(e)

    # Missing env
    try:
        service.analyze_regions(AnalyzeRegionsRequest(tenant_id="t1", env="", asset_id="a1"))
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "env is required" in str(e)
        
    # Context mismatch
    # Context mismatch
    from engines.common.identity import RequestContext
    ctx = RequestContext(tenant_id="t_test", env="dev", user_id="u1")
    try:
        service.analyze_regions(
            AnalyzeRegionsRequest(tenant_id="t_other", env="dev", asset_id="a1"), 
            context=ctx
        )
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "mismatch" in str(e)

