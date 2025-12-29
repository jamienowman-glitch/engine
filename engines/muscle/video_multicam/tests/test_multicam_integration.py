from unittest.mock import MagicMock
from engines.video_multicam.service import MultiCamService
from engines.align.service import AlignService
from engines.video_multicam.models import CreateMultiCamSessionRequest, MultiCamTrackSpec, MultiCamAlignRequest
from engines.media_v2.models import MediaAsset

def test_multicam_sync_integration():
    # Setup
    mock_media = MagicMock()
    mock_timeline = MagicMock()
    
    # Custom Align Service that uses our filename mock logic
    align_service = AlignService()
    
    service = MultiCamService(
        media_service=mock_media,
        timeline_service=mock_timeline,
        align_backend=align_service
    )
    
    # Data
    mock_media.get_asset.side_effect = lambda aid: MediaAsset(id=aid, tenant_id="t1", env="dev", kind="video", source_uri=f"/tmp/{aid}.mp4")
    
    # 1. Create Session
    req = CreateMultiCamSessionRequest(
        tenant_id="t1", env="dev", name="Test Session",
        tracks=[
            MultiCamTrackSpec(asset_id="cam_master", role="primary"),
            MultiCamTrackSpec(asset_id="cam_delayed", role="secondary"),
            MultiCamTrackSpec(asset_id="cam_advanced", role="alt")
        ],
        base_asset_id="cam_master"
    )
    session = service.create_session(req)
    assert len(session.tracks) == 3
    
    # 2. Align
    # Based on AlignService stub:
    # "delayed" -> 1000.0
    # "advanced" -> -500.0
    align_req = MultiCamAlignRequest(tenant_id="t1", env="dev", session_id=session.id)
    result = service.align_session(align_req)
    
    offsets = result.offsets_ms
    assert offsets["cam_master"] == 0
    assert offsets["cam_delayed"] == 1000
    assert offsets["cam_advanced"] == -500
    
    # Verify Session Updated
    updated = service.get_session(session.id)
    curr_offsets = {t.asset_id: t.offset_ms for t in updated.tracks}
    assert curr_offsets["cam_delayed"] == 1000

def test_build_sequence():
    mock_media = MagicMock()
    mock_timeline = MagicMock()
    align_service = AlignService()
    service = MultiCamService(media_service=mock_media, timeline_service=mock_timeline, align_backend=align_service)
    
    # Prepare Session with offsets
    from engines.video_multicam.models import MultiCamSession
    session = MultiCamSession(
        tenant_id="t1", env="dev", name="BuildTest",
        tracks=[
            MultiCamTrackSpec(asset_id="c1", offset_ms=0),
            MultiCamTrackSpec(asset_id="c2", offset_ms=1000), # starts 1s later
            MultiCamTrackSpec(asset_id="c3", offset_ms=-500)  # starts 0.5s earlier
        ],
        base_asset_id="c1"
    )
    service.repo.create(session)
    
    # Mocks for build
    mock_timeline.create_project.return_value = MagicMock(id="p1")
    mock_timeline.create_sequence.return_value = MagicMock(id="s1")
    mock_timeline.create_track.side_effect = lambda t: MagicMock(id=f"tr_{t.order}")
    mock_media.get_asset.return_value = MediaAsset(id="a", tenant_id="t1", env="dev", kind="video", duration_ms=10000, source_uri="/tmp/a.mp4")
    
    from engines.video_multicam.models import MultiCamBuildSequenceRequest
    req = MultiCamBuildSequenceRequest(tenant_id="t1", env="dev", session_id=session.id)
    
    res = service.build_sequence(req)
    
    # Check Clip Creation logic
    # We expect 3 clip calls
    assert mock_timeline.create_clip.call_count == 3
    calls = mock_timeline.create_clip.call_args_list
    
    # c1: offset 0. start_ms_on_timeline=0, in_ms=0
    # c2: offset 1000. start_ms=1000, in_ms=0
    # c3: offset -500. start_ms=0, in_ms=500 (cut head)
    
    # Let's inspect args
    # call args: (Clip(...),)
    clips = [c[0][0] for c in calls]
    c1 = next(c for c in clips if c.asset_id == "c1")
    c2 = next(c for c in clips if c.asset_id == "c2")
    c3 = next(c for c in clips if c.asset_id == "c3")
    
    assert c1.start_ms_on_timeline == 0
    assert c1.in_ms == 0
    
    assert c2.start_ms_on_timeline == 1000
    assert c2.in_ms == 0
    
    assert c3.start_ms_on_timeline == 0
    assert c3.in_ms == 500
