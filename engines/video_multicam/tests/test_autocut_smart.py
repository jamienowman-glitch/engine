import os
import pytest
from unittest.mock import MagicMock, patch
from engines.video_multicam.service import MultiCamService
from engines.video_multicam.models import CreateMultiCamSessionRequest, MultiCamAutoCutRequest, MultiCamTrackSpec, MultiCamSession
from engines.media_v2.models import MediaAsset, DerivedArtifact
from engines.video_timeline.models import Sequence, Track

@patch("engines.video_multicam.service.get_media_service")
@patch("engines.video_multicam.service.get_timeline_service")
@patch("engines.video_multicam.service.GcsClient")
@patch("engines.video_multicam.backend.HAS_DSP", True)
def test_autocut_smart_switch(mock_gcs, mock_tl_svc, mock_media_svc):
    # Setup Services
    mock_media = mock_media_svc.return_value
    mock_media.get_asset.side_effect = lambda aid: MediaAsset(id=aid, tenant_id="t1", env="dev", kind="video", duration_ms=10000, source_uri="mock://uri")
    
    mock_tl = mock_tl_svc.return_value
    # Mock sequence/track creation returning objects with IDs
    mock_tl.create_sequence.return_value = Sequence(id="seq1", project_id="p1", tenant_id="t1", env="dev", name="Cut")
    mock_tl.create_track.return_value = Track(id="track1", sequence_id="seq1", tenant_id="t1", env="dev", kind="video", order=0)
    
    svc = MultiCamService(media_service=mock_media, timeline_service=mock_tl)
    
    # Create Session manually in repo
    session = MultiCamSession(
        id="s1", tenant_id="t1", env="dev", name="Test",
        tracks=[
            MultiCamTrackSpec(asset_id="cam1", role="primary"),
            MultiCamTrackSpec(asset_id="cam2", role="alt")
        ]
    )
    svc.repo.create(session)
    
    # We want to force a switch.
    events_cam1 = [{"start_ms": 0, "end_ms": 2000}]
    events_cam2 = [{"start_ms": 2000, "end_ms": 4000}]

    art_cam1 = DerivedArtifact(
        id="sem_cam1", tenant_id="t1", env="dev", parent_asset_id="cam1",
        kind="audio_semantic_timeline", uri="mem://cam1", meta={"events": events_cam1}
    )
    art_cam2 = DerivedArtifact(
        id="sem_cam2", tenant_id="t1", env="dev", parent_asset_id="cam2",
        kind="audio_semantic_timeline", uri="mem://cam2", meta={"events": events_cam2}
    )

    def list_artifacts(aid):
        if aid == "cam1":
            return [art_cam1]
        if aid == "cam2":
            return [art_cam2]
        return []

    mock_media.list_artifacts_for_asset.side_effect = list_artifacts

    req = MultiCamAutoCutRequest(
        session_id="s1", tenant_id="t1", env="dev",
        min_shot_duration_ms=1000, max_shot_duration_ms=1500,
    )

    with patch.dict(os.environ, {"VIDEO_MULTICAM_PACING_PRESET": "fast"}):
        res = svc.auto_cut_sequence(req)

    assert res.meta["pacing_preset"] == "fast"
    assert res.meta["score_version"] == "v1"

    clips = [c[0][0] for c in mock_tl.create_clip.call_args_list]
    assert len(clips) >= 2

    durations = [(c.out_ms - c.in_ms) for c in clips[:2]]
    assert all(1000 <= dur <= 1500 for dur in durations)

    asset_ids = [c.asset_id for c in clips[:3]]
    assert asset_ids[0] == "cam1"
    assert "cam2" in asset_ids
