from unittest.mock import MagicMock, patch
from engines.video_render.service import RenderService
from engines.video_timeline.models import VideoProject, Sequence, Track, Clip, FilterStack, Filter
from engines.video_timeline.service import TimelineService
from engines.media_v2.models import MediaAsset, DerivedArtifact
from engines.video_render.models import RenderRequest

def test_render_with_region_filter():
    # Setup Services
    mock_timeline = MagicMock(spec=TimelineService)
    mock_media = MagicMock()
    service = RenderService()
    service.timeline_service = mock_timeline
    service.media_service = mock_media
    
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
    summary_art = DerivedArtifact(id="summary_1", parent_asset_id="a1", tenant_id="t1", env="dev", kind="video_region_summary", uri="/tmp/summary.json")
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
