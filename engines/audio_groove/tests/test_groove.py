import pytest
from unittest.mock import MagicMock, patch
from engines.audio_groove.service import AudioGrooveService, GrooveExtractRequest
from engines.audio_groove.dsp import extract_groove_offsets
from engines.audio_pattern_engine.service import AudioPatternEngineService
from engines.audio_pattern_engine.models import PatternRequest
from engines.media_v2.models import DerivedArtifact, MediaAsset
from engines.audio_groove.models import GrooveProfile

def test_extract_groove_service():
    mock_media = MagicMock()
    # Mock artifact with BPM
    mock_media.get_artifact.return_value = DerivedArtifact(
        id="loop1", parent_asset_id="p", tenant_id="t", env="d", kind="audio_loop", uri="/tmp/loop.wav",
        meta={"bpm": 120.0}
    )
    
    # Mock upload returning asset
    mock_media.register_upload.return_value = MediaAsset(id="prof_asset", tenant_id="t", env="d", kind="other", source_uri="/tmp/g.json")
    
    # Mock register artifact
    def fake_artifact(req):
        return DerivedArtifact(
            id="prof1", parent_asset_id=req.parent_asset_id, tenant_id=req.tenant_id,
            env=req.env, kind=req.kind, uri=req.uri, meta=req.meta
        )
    mock_media.register_artifact.side_effect = fake_artifact
    
    # Mock DSP
    with patch("engines.audio_groove.service.extract_groove_offsets") as mock_dsp, \
         patch("engines.audio_groove.service.open"), \
         patch("engines.audio_groove.service.Path") as mock_path:
         
        # Return 16 offsets. Let's say odd steps distinct.
        # Step 0: 0ms. Step 1: 10ms (late). Step 2: 0ms. Step 3: -5ms (early).
        fake_offsets = [0.0] * 16
        fake_offsets[1] = 10.0
        fake_offsets[3] = -5.0
        mock_dsp.return_value = fake_offsets
        
        mock_path.return_value.read_bytes.return_value = b"{}"
        mock_path.return_value.exists.return_value = True

        svc = AudioGrooveService(media_service=mock_media)
        req = GrooveExtractRequest(tenant_id="t", env="d", artifact_id="loop1")
        
        res = svc.extract_groove(req)
        
        assert res.artifact_id == "prof1"
        assert res.profile.offsets[1] == 10.0
        assert res.profile.offsets[3] == -5.0
        assert res.profile.subdivision == 16
        assert res.meta["subdivision"] == 16


def test_extract_groove_subdivision_normalization():
    mock_librosa = MagicMock()
    mock_librosa.load.return_value = (MagicMock(), 22050)
    mock_librosa.onset.onset_detect.return_value = [0, 10, 20]
    mock_librosa.frames_to_time.return_value = [0.0, 0.25, 0.5]
    with patch.dict("sys.modules", {"librosa": mock_librosa, "librosa.onset": mock_librosa.onset}):
        offsets = extract_groove_offsets("dummy.wav", 120, subdivision=7)
        assert len(offsets) == 8
        assert offsets[0] == 0.0
        assert offsets[1] >= -500.0  # values exist even when sparse


def test_extract_groove_subdivision_32():
    mock_librosa = MagicMock()
    mock_librosa.load.return_value = (MagicMock(), 22050)
    mock_librosa.onset.onset_detect.return_value = list(range(0, 100, 3))
    mock_librosa.frames_to_time.return_value = [i * 0.0625 for i in range(len(mock_librosa.onset.onset_detect.return_value))]
    with patch.dict("sys.modules", {"librosa": mock_librosa, "librosa.onset": mock_librosa.onset}):
        offsets = extract_groove_offsets("dummy.wav", 120, subdivision=32)
        assert len(offsets) == 32
        assert all(isinstance(offset, float) for offset in offsets)

def test_pattern_apply_groove():
    # Test integration in Pattern Engine
    # We mock get_audio_groove_service to return a specific profile
    
    with patch("engines.audio_pattern_engine.service.get_audio_groove_service") as mock_get_svc:
        mock_g_svc = MagicMock()
        mock_get_svc.return_value = mock_g_svc
        
        # Profile: 16 steps. Step 1 (2nd 16th) has +20ms offset.
        offsets = [0.0] * 16
        offsets[1] = 20.0
        mock_g_svc.get_groove_profile.return_value = GrooveProfile(bpm=120, subdivision=16, offsets=offsets)
        
        svc = AudioPatternEngineService()
        req = PatternRequest(
            tenant_id="t", env="d", template_id="four_on_the_floor",
            sample_map={"hat": "h1"}, # Hat 3,7,11,15 (indices 2,6,10,14)
            # Wait, "four_on_the_floor" hat indices are 2, 6, 10, 14 (3rd, 7th...)
            # These are EVEN indices (0, 1, 2...). 2 is even.
            # My logic in profile was Step 1.
            # Let's adjust sample map or target.
            # four_on_the_floor kick is 0, 4, 8, 12.
            # Let's check a template with odd notes.
            # boom_bap_90 has 16th hats (steps_fill). 
            # Step 1 (2nd 16th) should be shifted.
        )
        
        # Let's use boom_bap_90 for test, forcing BPM 120
        req.template_id = "boom_bap_90"
        req.bpm = 120.0
        req.sample_map = {"hat": "h1"}
        req.groove_profile_id = "prof1"
        req.swing_pct = 0.0 # Ensure swing doesn't interfere (should be overridden anyway)
        
        res = svc.generate_pattern(req)
        clips = res.clips
        
        # Step 0 (0ms) -> Offset 0
        c0 = next(c for c in clips if c["start_ms"] == 0.0)
        assert c0
        
        # Step 1 (125ms base). Should have +20ms -> 145ms.
        # Find clip closest to 145
        c1 = next((c for c in clips if abs(c["start_ms"] - 145.0) < 1.0), None)
        assert c1 is not None, "Step 1 clip not found at expected groove offset"
