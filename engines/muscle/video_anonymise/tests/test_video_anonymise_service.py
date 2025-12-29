from unittest.mock import MagicMock
from engines.video_anonymise.service import VideoAnonymiseService
from engines.video_anonymise.models import AnonymiseFacesRequest
from engines.video_regions.models import AnalyzeRegionsResult, RegionAnalysisSummary, RegionMaskEntry
from engines.video_timeline.models import Track, Clip, FilterStack, Filter

def test_anonymise_sequence_adds_filter():
    # Mocks
    mock_timeline = MagicMock()
    mock_regions = MagicMock()
    
    # 1 video track with 1 clip
    mock_timeline.list_tracks_for_sequence.return_value = [Track(id="t1", sequence_id="s1", tenant_id="t", env="d", kind="video")]
    mock_timeline.list_clips_for_track.return_value = [Clip(id="c1", track_id="t1", asset_id="a1", duration_ms=100, start_ms_on_timeline=0, in_ms=0, out_ms=100, tenant_id="t", env="d")]
    
    # Default stack is None (no filters)
    mock_timeline.get_filter_stack_for_target.return_value = None
    
    # Summary says "face" exists
    summary = RegionAnalysisSummary(
        tenant_id="t", env="d", asset_id="a1",
        entries=[RegionMaskEntry(time_ms=0, region="face", mask_artifact_id="m1")],
        meta={"backend_version": "video_regions_stub_v1"}
    )
    # Regions analysis returns hits
    mock_regions.analyze_regions.return_value = AnalyzeRegionsResult(summary_artifact_id="art1", summary=summary)
    mock_regions.get_analysis.return_value = summary
    
    service = VideoAnonymiseService(timeline_service=mock_timeline, regions_service=mock_regions)
    
    req = AnonymiseFacesRequest(tenant_id="t", env="d", sequence_id="s1", filter_strength=0.9)
    res = service.anonymise_sequence(req)
    
    # Verified
    assert res.clips_modified_count == 1
    assert "c1" in res.clip_ids
    
    # Check filter creation
    mock_timeline.create_filter_stack.assert_called_once()
    args = mock_timeline.create_filter_stack.call_args[0]
    stack = args[0]
    assert len(stack.filters) == 1
    assert stack.filters[0].type == "face_blur"
    assert stack.filters[0].params["strength"] == 0.9
    assert stack.filters[0].params["backend_version"] == "video_regions_stub_v1"
    assert stack.filters[0].params["source_summary_id"] == "art1"

def test_anonymise_no_faces():
    mock_timeline = MagicMock()
    mock_regions = MagicMock()
    
    mock_timeline.list_tracks_for_sequence.return_value = [Track(id="t1", sequence_id="s1", tenant_id="t", env="d", kind="video")]
    mock_timeline.list_clips_for_track.return_value = [Clip(id="c1", track_id="t1", asset_id="a1", duration_ms=100, start_ms_on_timeline=0, in_ms=0, out_ms=100, tenant_id="t", env="d")]
    
    # No faces
    summary = RegionAnalysisSummary(tenant_id="t", env="d", asset_id="a1", entries=[])
    mock_regions.analyze_regions.return_value = AnalyzeRegionsResult(summary_artifact_id="art1", summary=summary)
    mock_regions.get_analysis.return_value = summary
    
    service = VideoAnonymiseService(timeline_service=mock_timeline, regions_service=mock_regions)
    req = AnonymiseFacesRequest(tenant_id="t_test", env="d", sequence_id="s1")
    res = service.anonymise_sequence(req)
    
    assert res.clips_modified_count == 0
    mock_timeline.create_filter_stack.assert_not_called()

def test_anonymise_tenant_rejection():
    """Verify tenant mismatch with context raises ValueError."""
    from engines.common.identity import RequestContext
    service = VideoAnonymiseService(timeline_service=MagicMock(), regions_service=MagicMock())
    
    # Mismatch
    req = AnonymiseFacesRequest(tenant_id="t_test", env="dev", sequence_id="s1")
    ctx = RequestContext(tenant_id="t_other", env="dev", request_id="req1")
    
    import pytest
    with pytest.raises(ValueError, match="tenant/env mismatch"):
        service.anonymise_sequence(req, context=ctx)

def test_anonymise_missing_summary():
    """Verify behavior when regions service returns result but get_analysis returns None (e.g. race condition/corruption)."""
    mock_timeline = MagicMock()
    mock_regions = MagicMock()
    
    mock_timeline.list_tracks_for_sequence.return_value = [Track(id="t1", sequence_id="s1", tenant_id="t", env="d", kind="video")]
    mock_timeline.list_clips_for_track.return_value = [Clip(id="c1", track_id="t1", asset_id="a1", duration_ms=100, start_ms_on_timeline=0, in_ms=0, out_ms=100, tenant_id="t", env="d")]
    
    # Analyze returns result (with valid summary obj to pass validation), but get_analysis returns None
    dummy = RegionAnalysisSummary(tenant_id="t", env="d", asset_id="a1", entries=[])
    mock_regions.analyze_regions.return_value = AnalyzeRegionsResult(summary_artifact_id="art_gone", summary=dummy)
    mock_regions.get_analysis.return_value = None
    
    service = VideoAnonymiseService(timeline_service=mock_timeline, regions_service=mock_regions)
    req = AnonymiseFacesRequest(tenant_id="t_test", env="d", sequence_id="s1")
    
    # Should run without error but do nothing
    res = service.anonymise_sequence(req)
    assert res.clips_modified_count == 0
