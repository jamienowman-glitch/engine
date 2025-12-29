import os
import pytest
from unittest.mock import MagicMock, patch
from engines.audio_timeline.service import AudioTimelineService
from engines.audio_render.service import AudioRenderService
from engines.audio_render.models import RenderRequest
from engines.media_v2.models import MediaAsset, DerivedArtifact
from engines.media_v2.service import MediaService

FIXTURE_PATH = os.path.abspath("engines/audio_hits/tests/fixtures/audio_hit.wav")

@pytest.fixture
def mock_media_service():
    m = MagicMock(spec=MediaService)
    
    # Mock asset retrieval
    def fake_get_asset(aid):
        if aid == "asset_hit":
             return MediaAsset(
                id="asset_hit", tenant_id="t", env="d", kind="audio", source_uri=FIXTURE_PATH
             )
        return None
    m.get_asset.side_effect = fake_get_asset
    
    # Mock upload/artifact
    def fake_upload(req, filename, content):
        return MediaAsset(
            id="asset_render_out", tenant_id="t", env="d", kind="audio", source_uri=f"/tmp/{filename}"
        )
    m.register_upload.side_effect = fake_upload
    
    def fake_artifact(req):
        return DerivedArtifact(
             id="art_render_1",
             parent_asset_id="asset_render_out",
             tenant_id=req.tenant_id,
             env=req.env,
             kind=req.kind,
             uri=req.uri,
             meta=req.meta
        )
    m.register_artifact.side_effect = fake_artifact
    
    return m

def test_render_mix(mock_media_service):
    if not os.path.exists(FIXTURE_PATH):
        pytest.skip(f"Fixture not found {FIXTURE_PATH}")
        
    tl = AudioTimelineService()
    seq = tl.create_sequence("t1", "dev", bpm=120)
    
    # Track 1
    t1 = tl.add_track(seq, "Drums")
    
    # Clip 1 at 0ms
    tl.add_clip(t1, start_ms=0, asset_id="asset_hit", duration_ms=500)
    
    # Clip 2 at 1000ms
    tl.add_clip(t1, start_ms=1000, asset_id="asset_hit", duration_ms=500)
    
    # Render
    rnd = AudioRenderService(media_service=mock_media_service)
    req = RenderRequest(sequence=seq)

    with patch("engines.audio_render.service.subprocess.run") as mock_run, \
         patch("engines.audio_render.service.Path") as mock_path:
        mock_run.return_value = MagicMock(returncode=0)
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.read_bytes.return_value = b"render-data"
        mock_path.return_value.unlink.return_value = None
        res = rnd.render_sequence(req)
    
    assert res.artifact_id == "art_render_1"
    assert res.uri.startswith("/tmp/")

def test_render_plan_logic(mock_media_service):
    # Verify the plan without running ffmpeg
    from engines.audio_render.planner import build_ffmpeg_mix_plan
    
    tl = AudioTimelineService()
    seq = tl.create_sequence("t1", "dev")
    t1 = tl.add_track(seq)
    
    # Clip A at 500ms
    tl.add_clip(t1, start_ms=500, asset_id="asset_hit", duration_ms=200)
    
    inputs, flt, maps, metadata = build_ffmpeg_mix_plan(seq, mock_media_service)
    
    # Check inputs
    assert len(inputs) == 1
    assert inputs[0] == FIXTURE_PATH
    
    # Check adelay=500
    assert "adelay=500|500" in flt
    # Check mix
    assert "amix" in flt
    assert "master" in metadata
