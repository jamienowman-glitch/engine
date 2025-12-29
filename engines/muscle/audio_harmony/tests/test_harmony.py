import pytest
from unittest.mock import MagicMock, patch
from engines.audio_harmony.service import AudioHarmonyService, HarmonyRequest, KeyEstimate
from engines.media_v2.models import DerivedArtifact, MediaAsset
from engines.audio_resample.models import ResampleResult

def test_detect_key():
    mock_media = MagicMock()
    art = DerivedArtifact(
        id="a1", parent_asset_id="p", tenant_id="t", env="d", kind="audio_loop", uri="/tmp/audio.wav", meta={}
    )
    mock_media.get_artifact.return_value = art
    
    # Mock estimate_key directly (to skip librosa)
    with patch("engines.audio_harmony.service.estimate_key") as mock_est:
        mock_est.return_value = KeyEstimate(root="G", scale="major", confidence=0.9)
        
        svc = AudioHarmonyService(media_service=mock_media)
        est = svc.detect_key("a1")
        
        assert est.root == "G"
        assert art.meta["key_root"] == "G"

def test_adapt_to_key_logic():
    mock_media = MagicMock()
    # Source Key: C
    art = DerivedArtifact(
        id="a1", parent_asset_id="p", tenant_id="t", env="d", kind="audio_loop", uri="u", 
        meta={"key_root": "C"}
    )
    mock_media.get_artifact.return_value = art
    
    mock_resample = MagicMock()
    mock_resample.resample_artifact.return_value = ResampleResult(
        artifact_id="res1", uri="u2", duration_ms=1000
    )
    
    svc = AudioHarmonyService(media_service=mock_media, resample_service=mock_resample)
    
    # Target: G.
    # C(0) -> G(7). Dist +7.
    # Shortest path: +7 > 6 -> +7 - 12 = -5.
    
    req = HarmonyRequest(tenant_id="t", env="d", artifact_id="a1", target_key_root="G")
    res = svc.adapt_to_key(req)
    
    args = mock_resample.resample_artifact.call_args[0][0] # First arg (req)
    assert args.pitch_semitones == -5 # or 7 depending on logic. I implemented wrap > 6.
    assert res.artifact_id == "res1"
