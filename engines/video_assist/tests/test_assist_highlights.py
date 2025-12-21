import pytest
from unittest.mock import MagicMock, patch
from engines.video_assist.service import VideoAssistService
from engines.video_timeline.models import VideoProject, Sequence, Track, Clip
from engines.media_v2.models import MediaAsset, DerivedArtifact

@patch("engines.video_assist.service.get_media_service")
@patch("engines.video_assist.service.get_timeline_service")
def test_generate_highlights(mock_tl_svc, mock_media_svc):
    mock_media = mock_media_svc.return_value
    a1 = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", source_uri="/tmp/1.mp4", duration_ms=60000)
    a2 = MediaAsset(id="a2", tenant_id="t1", env="dev", kind="video", source_uri="/tmp/2.mp4", duration_ms=60000)

    def side_effect_get_asset(aid):
        if aid == "a1":
            return a1
        if aid == "a2":
            return a2
        return None

    mock_media.get_asset.side_effect = side_effect_get_asset

    sem1 = DerivedArtifact(
        id="sem1", tenant_id="t1", env="dev", parent_asset_id="a1",
        kind="audio_semantic_timeline", uri="mem://1",
        meta={"events": [{"start_ms": 0, "end_ms": 3000, "confidence": 0.9}]},
    )
    sem2 = DerivedArtifact(
        id="sem2", tenant_id="t1", env="dev", parent_asset_id="a2",
        kind="audio_semantic_timeline", uri="mem://2",
        meta={"events": [{"start_ms": 1000, "end_ms": 4000, "confidence": 0.6}]},
    )
    vis1 = DerivedArtifact(
        id="vis1", tenant_id="t1", env="dev", parent_asset_id="a1",
        kind="visual_meta", uri="vis://1",
        meta={"frames": [{"timestamp_ms": 500, "motion_score": 0.9}]},
    )
    vis2 = DerivedArtifact(
        id="vis2", tenant_id="t1", env="dev", parent_asset_id="a2",
        kind="visual_meta", uri="vis://2",
        meta={"frames": [{"timestamp_ms": 1500, "motion_score": 0.4}]},
    )

    def list_artifacts(aid):
        if aid == "a1":
            return [sem1, vis1]
        if aid == "a2":
            return [sem2, vis2]
        return []

    mock_media.list_artifacts_for_asset.side_effect = list_artifacts
    
    mock_tl = mock_tl_svc.return_value
    # Existing project structure
    mock_tl.get_project.return_value = VideoProject(id="p1", tenant_id="t1", env="dev", title="AssistProj", sequence_ids=["s_orig"])
    
    # Existing sequence with tracks/clips
    t_orig = Track(id="t_orig", sequence_id="s_orig", tenant_id="t1", env="dev", kind="video")
    mock_tl.list_tracks_for_sequence.return_value = [t_orig]
    
    # Clips validation
    c1 = Clip(id="c1", track_id="t_orig", tenant_id="t1", env="dev", asset_id="a1", start_ms_on_timeline=0, in_ms=0, out_ms=10000)
    c2 = Clip(id="c2", track_id="t_orig", tenant_id="t1", env="dev", asset_id="a2", start_ms_on_timeline=10000, in_ms=0, out_ms=10000)
    mock_tl.list_clips_for_track.return_value = [c1, c2]
    
    svc = VideoAssistService()
    
    # Generate 10s highlight reel
    # Fallback logic takes 3s from middle of each asset.
    # a1 and a2 are both > 5s duration.
    # So we expect 2 clips of 3s each = 6s total (if target is large enough)
    # Target 30s.
    
    seq, track, clips = svc.generate_highlights("p1", target_duration_ms=4000)
    
    assert seq.project_id == "p1"
    assert "Highlights" in seq.name
    assert track.meta["highlight_score_version"] == "v1"
    assert len(clips) >= 2

    first, second = clips[0], clips[1]
    assert first.asset_id == "a1"
    assert second.asset_id == "a2"
    assert first.out_ms - first.in_ms == 3000
    assert second.out_ms - second.in_ms == 3000
