import os
from pathlib import Path

import pytest
from unittest.mock import MagicMock, patch

from engines.audio_normalise.service import AudioNormaliseService, NormaliseRequest
from engines.audio_shared.health import DependencyInfo
from engines.media_v2.models import MediaAsset, DerivedArtifact
from engines.media_v2.service import MediaService

FIXTURE_PATH = os.path.abspath("engines/audio_hits/tests/fixtures/audio_hit.wav")
MOCK_FEATURES = {"brightness": 1000.0, "key_root": "B"}


def _fake_dependencies() -> dict[str, DependencyInfo]:
    return {
        "ffmpeg": DependencyInfo(True, "6.1", None),
        "ffprobe": DependencyInfo(True, "6.1", None),
        "demucs": DependencyInfo(True, "4.1", None),
        "librosa": DependencyInfo(True, "0.10", None),
    }


def _fake_normalize_audio(input_path, output_path, target_lufs, peak_ceiling):
    Path(output_path).write_bytes(b"normalized")
    return {
        "input_i": -10.0,
        "output_i": target_lufs,
        "output_tp": peak_ceiling,
    }


def _fake_extract_features(path):
    return MOCK_FEATURES.copy()

@pytest.fixture
def mock_media_service():
    m = MagicMock(spec=MediaService)
    
    m.get_asset.return_value = MediaAsset(
        id="asset_test",
        tenant_id="t1",
        env="dev",
        kind="audio",
        source_uri=FIXTURE_PATH
    )
    
    def fake_upload(req, filename, content):
        return MediaAsset(
            id="asset_norm_out",
            tenant_id=req.tenant_id,
            env=req.env,
            kind="audio",
            source_uri=f"/tmp/{filename}"
        )
    m.register_upload.side_effect = fake_upload
    
    def fake_artifact(req):
        return DerivedArtifact(
             id="art_norm_1",
             parent_asset_id=req.parent_asset_id,
             tenant_id=req.tenant_id,
             env=req.env,
             kind=req.kind,
             uri=req.uri,
             meta=req.meta
        )
    m.register_artifact.side_effect = fake_artifact
    
    return m

def test_normalise_and_tag(mock_media_service):
    if not os.path.exists(FIXTURE_PATH):
        pytest.skip("Fixture not found")
        
    svc = AudioNormaliseService(media_service=mock_media_service)
    
    req = NormaliseRequest(
        tenant_id="t1", env="dev",
        asset_id="asset_test",
        target_lufs=-14.0,
        peak_ceiling_dbfs=-2.0
    )
    
    with patch("engines.audio_normalise.service.check_dependencies") as mock_check, \
         patch("engines.audio_normalise.service.normalize_audio", side_effect=_fake_normalize_audio), \
         patch("engines.audio_normalise.service.extract_features_librosa", side_effect=_fake_extract_features):
        mock_check.return_value = _fake_dependencies()
        res = svc.normalise_asset(req)
    
    assert res.artifact_id == "art_norm_1"
    assert "norm_" in res.uri 
    
    # Check stats
    # Stats might be empty if parsing failed, but keys should exist if successful run?
    # Our dsp parsing is loose.
    # Note: ffmpeg loudnorm prints to stderr, which we capture.
    
    # Check features
    assert res.tags is not None
    # 1000Hz sine -> Centroid ~1000.
    # Allow loose check
    if res.tags.brightness:
        assert 900 < res.tags.brightness < 1100
        
    # Key? 1000Hz is close to B.
    if res.tags.key_root:
        assert res.tags.key_root in ["B", "C"] # 987Hz is B, 1046 is C. 1000 is closer to B.

    assert res.meta["backend_info"]["backend_type"] == "ffmpeg"
    assert res.meta["target_lufs"] == -14.0
    assert res.meta["peak_ceiling_dbfs"] == -2.0
    assert res.meta["norm_stats"]["output_i"] == -14.0
    assert res.meta["features"] == MOCK_FEATURES

def test_tag_only_skip_norm(mock_media_service):
    if not os.path.exists(FIXTURE_PATH):
        pytest.skip("Fixture not found")

    svc = AudioNormaliseService(media_service=mock_media_service)
    
    req = NormaliseRequest(
        tenant_id="t1", env="dev",
        asset_id="asset_test",
        skip_normalization=True
    )
    
    with patch("engines.audio_normalise.service.check_dependencies") as mock_check, \
         patch("engines.audio_normalise.service.normalize_audio", side_effect=_fake_normalize_audio), \
         patch("engines.audio_normalise.service.extract_features_librosa", side_effect=_fake_extract_features):
        mock_check.return_value = _fake_dependencies()
        res = svc.normalise_asset(req)
    
    # Should be no new artifact if we didn't implement logic to create one for skip=True?
    # service.py implemented: "if out_path and out_path.exists(): ... else: pass"
    # So artifact_id might be None.
    
    assert res.artifact_id is None
    assert res.tags is not None
    if res.tags.brightness:
        assert 900 < res.tags.brightness < 1100
    assert res.meta["backend_info"]["backend_type"] == "ffmpeg"
    assert res.meta["norm_stats"] == {}
