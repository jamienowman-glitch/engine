from unittest.mock import MagicMock, patch
from engines.video_render.service import RenderService
from engines.video_timeline.models import VideoProject, Sequence, Track, Clip, FilterStack, Filter
from engines.video_timeline.service import TimelineService
from engines.media_v2.models import MediaAsset, DerivedArtifact
from engines.video_render.models import RenderRequest

@patch("engines.video_render.service.get_media_service")
def test_render_with_region_filter(mock_get_media):
    # Setup Services
    mock_timeline = MagicMock(spec=TimelineService)
    mock_media = mock_get_media.return_value
    service = RenderService()
    service.timeline_service = mock_timeline
    # service.media_service is already set by constructor via mock
    
    # Data Setup
    proj = VideoProject(id="p1", tenant_id="t1", env="dev", title="P1")
    seq = Sequence(id="s1", tenant_id="t1", env="dev", project_id="p1", name="S1")
    track = Track(id="tr1", tenant_id="t1", env="dev", sequence_id="s1", kind="video")
    clip = Clip(id="c1", tenant_id="t1", env="dev", track_id="tr1", asset_id="a1", in_ms=0, out_ms=1000, start_ms_on_timeline=0)
    
    mock_timeline.get_project.return_value = proj
    mock_timeline.list_sequences_for_project.return_value = [seq]
    mock_timeline.list_tracks_for_sequence.return_value = [track]
    mock_timeline.list_clips_for_track.return_value = [clip]
    mock_timeline.list_automation.return_value = []
    
    # Asset
    mock_media.get_asset.return_value = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", source_uri="gs://in.mp4")
    
    # Filter Stack
    stack = FilterStack(id="fs1", tenant_id="t1", env="dev", target_type="clip", target_id="c1", filters=[
        Filter(type="teeth_whiten", params={"intensity": 0.8})
    ])
    mock_timeline.get_filter_stack_for_target.return_value = stack
    
    # Region Analysis Artifact
    summary_art = DerivedArtifact(
        id="summary_1", 
        parent_asset_id="a1", 
        tenant_id="t1", 
        env="dev", 
        kind="video_region_summary", 
        uri="/tmp/summary.json",
        meta={"backend_version": "v1", "model_used": "m1", "cache_key": "k1"}
    )
    mask_art = DerivedArtifact(id="mask_teeth", parent_asset_id="a1", tenant_id="t1", env="dev", kind="mask", uri="/tmp/teeth.png")
    
    # Mock list_artifacts to return summary
    mock_media.list_artifacts_for_asset.return_value = [summary_art]
    # Mock get_artifact to return summary or mask
    def get_artifact(aid):
        if aid == "summary_1": return summary_art
        if aid == "mask_teeth": return mask_art
        return None
    mock_media.get_artifact.side_effect = get_artifact
    
    # Mock Reading Summary JSON
    # We patch open() in resolve_region_masks_for_clip or patch the whole function
    # Let's patch resolve_region_masks_for_clip in service
    # Actually, simpler to patch keys in `extensions.py` but that's imported inside service.
    # Because of `from engines.video_render.extensions import ...` inside method, we patch where it is used or patch the module.
    
    with patch("engines.video_render.extensions.resolve_region_masks_for_clip") as mock_resolve:
        # Mock it to return our mask map
        mock_resolve.return_value = {0: "/tmp/teeth.png"}
        
        req = RenderRequest(tenant_id="t1", env="dev", project_id="p1")
        plan = service._build_plan(req)
        
        # Verify
        filters = plan.filters
        # Should contain split logic
        assert any("split" in f for f in filters)
        assert any("alphamerge" in f for f in filters)
        assert any("overlay=" in f for f in filters)
        
        # Verify intensity params
        # brightness=0.16 (0.8*0.2)
        assert any("brightness=0.16" in f for f in filters)

        # Verify inputs included the mask
        assert "/tmp/teeth.png" in plan.inputs
    args = ["ffmpeg"]
    # ... mocked ffmpeg args check not strictly needed here as we check plan inputs
    
@patch("engines.video_render.service.get_media_service")
def test_dependency_notices_presence(mock_get_media):
    """Verify plan meta contains notices for present artifacts."""
    mock_timeline = MagicMock(spec=TimelineService)
    mock_media = mock_get_media.return_value
    service = RenderService()
    service.timeline_service = mock_timeline
    
    # Setup Data
    proj = VideoProject(id="p1", tenant_id="t1", env="dev", title="TestProject")
    seq = Sequence(id="s1", tenant_id="t1", env="dev", project_id="p1", name="Seq1")
    track = Track(id="tr1", tenant_id="t1", env="dev", sequence_id="s1", kind="video")
    clip = Clip(id="c1", tenant_id="t1", env="dev", track_id="tr1", asset_id="a1", in_ms=0, out_ms=1000, start_ms_on_timeline=0)
    
    mock_timeline.get_project.return_value = proj
    mock_timeline.list_sequences_for_project.return_value = [seq]
    mock_timeline.list_tracks_for_sequence.return_value = [track]
    mock_timeline.list_clips_for_track.return_value = [clip]
    mock_timeline.list_automation.return_value = []
    
    # Needs filter to trigger video_regions dependency
    stack = FilterStack(id="fs1", tenant_id="t1", env="dev", target_type="clip", target_id="c1", filters=[
        Filter(type="teeth_whiten", params={"intensity": 0.5})
    ])
    mock_timeline.get_filter_stack_for_target.return_value = stack
    
    # Asset with artifacts
    mock_media.get_asset.return_value = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", source_uri="gs://in.mp4")
    
    # Artifacts
    arts = [
        DerivedArtifact(
            id="sum1", parent_asset_id="a1", tenant_id="t1", env="dev", kind="video_region_summary", 
            uri="/tmp/s.json", meta={"backend_version": "v1.0", "model_used": "m1", "cache_key": "k1"}
        ),
        DerivedArtifact(
            id="vm1", parent_asset_id="a1", tenant_id="t1", env="dev", kind="visual_meta", 
            uri="/tmp/v.json", meta={"backend_version": "v0.9", "model_used": "m2", "cache_key": "k2"}
        )
    ]
    mock_media.list_artifacts_for_asset.return_value = arts
    
    with patch("engines.video_render.extensions.resolve_region_masks_for_clip") as mock_resolve:
         # Need valid return to avoid warnings being principal output?
         mock_resolve.return_value = {0: "/tmp/mask.png"}
         
         req = RenderRequest(tenant_id="t1", env="dev", project_id="p1")
         plan = service._build_plan(req)
    
    assert "dependency_notices" in plan.meta
    notices = plan.meta["dependency_notices"]
    # notices is a list of dicts
    # Expect: [{'type': 'video_regions', 'asset_id': 'a1', 'requirement': ['teeth'], 'status': 'available', ...}, {'type': 'visual_meta', ...}]
    
    has_regions = any(n["type"] == "video_regions" and n["asset_id"] == "a1" and n["status"] == "available" for n in notices)
    has_visual = any(n["type"] == "visual_meta" and n["asset_id"] == "a1" and n["status"] == "available" for n in notices)
    assert has_regions
    assert has_visual


@patch("engines.video_render.service.get_media_service")
def test_missing_artifact_warnings(mock_get_media):
    """Verify warnings when artifacts are expected but missing for region filters."""
    mock_timeline = MagicMock(spec=TimelineService)
    mock_media = mock_get_media.return_value
    service = RenderService()
    service.timeline_service = mock_timeline
    
    proj = VideoProject(id="p1", tenant_id="t1", env="dev", title="MissingWarnProject")
    seq = Sequence(id="s1", tenant_id="t1", env="dev", project_id="p1", name="Seq1")
    track = Track(id="tr1", tenant_id="t1", env="dev", sequence_id="s1", kind="video")
    clip = Clip(id="c1", tenant_id="t1", env="dev", track_id="tr1", asset_id="a1", in_ms=0, out_ms=1000, start_ms_on_timeline=0)
    
    mock_timeline.get_project.return_value = proj
    mock_timeline.list_sequences_for_project.return_value = [seq]
    mock_timeline.list_tracks_for_sequence.return_value = [track]
    mock_timeline.list_clips_for_track.return_value = [clip]
    mock_timeline.list_automation.return_value = []
    
    mock_media.get_asset.return_value = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", source_uri="gs://in.mp4")
    
    # Filter Stack requesting teeth whiten
    stack = FilterStack(id="fs1", tenant_id="t1", env="dev", target_type="clip", target_id="c1", filters=[
        Filter(type="teeth_whiten", params={"intensity": 0.5})
    ])
    mock_timeline.get_filter_stack_for_target.return_value = stack
    
    # NO Artifacts found
    mock_media.list_artifacts_for_asset.return_value = []
    
    # resolve_region_masks_for_clip wil return empty
    with patch("engines.video_render.extensions.resolve_region_masks_for_clip") as mock_resolve:
        mock_resolve.return_value = {}
        
        req = RenderRequest(tenant_id="t1", env="dev", project_id="p1")
        plan = service._build_plan(req)
        
        assert "render_warnings" in plan.meta
        warnings = plan.meta["render_warnings"]
        # Can check for specific warning text from filter_warnings
        assert any("missing_region_mask_for_teeth_whiten_clip_c1" in w for w in warnings)
