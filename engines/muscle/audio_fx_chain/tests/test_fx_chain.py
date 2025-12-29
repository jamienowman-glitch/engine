import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from unittest.mock import MagicMock, patch

from engines.audio_fx_chain.service import AudioFxChainService
from engines.audio_fx_chain.models import FxChainRequest
from engines.audio_shared.health import DependencyInfo, DependencyMissingError
from engines.media_v2.models import MediaAsset, DerivedArtifact, MediaUploadRequest, ArtifactCreateRequest
from engines.media_v2.service import MediaService

# Use a real fixture path
FIXTURE_PATH = os.path.abspath("engines/audio_hits/tests/fixtures/audio_hit.wav")


def _fake_dependencies(ffmpeg_available: bool) -> dict[str, DependencyInfo]:
    return {
        "ffmpeg": DependencyInfo(ffmpeg_available, "6.1" if ffmpeg_available else None, None if ffmpeg_available else "missing"),
        "ffprobe": DependencyInfo(True, "6.1", None),
        "demucs": DependencyInfo(True, "4.1", None),
        "librosa": DependencyInfo(True, "0.10", None),
    }


def _fake_subprocess_run(cmd, check, stdout, stderr):
    out_path = Path(cmd[-1])
    out_path.write_bytes(b"fx")
    return SimpleNamespace(returncode=0)

@pytest.fixture
def mock_media_service():
    m = MagicMock(spec=MediaService)
    
    # Mock get_asset to return our fixture
    m.get_asset.return_value = MediaAsset(
        id="asset_test",
        tenant_id="t1",
        env="dev",
        kind="audio",
        source_uri=FIXTURE_PATH
    )
    
    # Mock register_upload to just return a dummy asset
    def fake_upload(req, filename, content):
        return MediaAsset(
            id="asset_fx_out",
            tenant_id=req.tenant_id,
            env=req.env,
            kind="audio",
            source_uri=f"/tmp/{filename}"
        )
    m.register_upload.side_effect = fake_upload
    
    # Mock register_artifact
    def fake_artifact(req):
        return DerivedArtifact(
             id="art_fx_1",
             parent_asset_id=req.parent_asset_id,
             tenant_id=req.tenant_id,
             env=req.env,
             kind=req.kind,
             uri=req.uri,
             meta=req.meta
        )
    m.register_artifact.side_effect = fake_artifact
    
    return m

def test_apply_fx_clean_hit(mock_media_service):
    if not os.path.exists(FIXTURE_PATH):
        pytest.skip(f"Fixture not found: {FIXTURE_PATH}")
        
    svc = AudioFxChainService(media_service=mock_media_service)
    
    req = FxChainRequest(
        tenant_id="t1", 
        env="dev",
        asset_id="asset_test",
        preset_id="clean_hit"
    )
    
    with patch("engines.audio_fx_chain.service.check_dependencies") as mock_check, \
         patch("engines.audio_fx_chain.service.subprocess.run", side_effect=_fake_subprocess_run):
        mock_check.return_value = _fake_dependencies(True)
        res = svc.apply_fx(req)
    
    assert res.preset_id == "clean_hit"
    assert res.params_applied["hpf_hz"] == 60
    assert "fx_" in res.uri 
    assert res.meta["fx_preset_id"] == "clean_hit"
    assert res.meta["preset_metadata"]["intensity"] == 0.4
    assert res.meta["knob_overrides"] == {}
    assert res.meta["backend_info"]["backend_type"] == "ffmpeg"
    assert res.meta["dry_wet"] == 1.0

def test_apply_fx_lofi_crunch(mock_media_service):
    if not os.path.exists(FIXTURE_PATH):
        pytest.skip(f"Fixture not found: {FIXTURE_PATH}")

    svc = AudioFxChainService(media_service=mock_media_service)
    
    req = FxChainRequest(
        tenant_id="t1", 
        env="dev",
        asset_id="asset_test",
        preset_id="lofi_crunch"
    )

    with patch("engines.audio_fx_chain.service.check_dependencies") as mock_check, \
         patch("engines.audio_fx_chain.service.subprocess.run", side_effect=_fake_subprocess_run):
        mock_check.return_value = _fake_dependencies(True)
        res = svc.apply_fx(req)
    
    assert res.preset_id == "lofi_crunch"
    # Verify bitcrusher params implicitly by success
    assert res.params_applied["sat"]["type"] == "hard"
    assert res.meta["backend_info"]["backend_type"] == "ffmpeg"

def test_apply_fx_override_clamps(mock_media_service):
    if not os.path.exists(FIXTURE_PATH):
        pytest.skip(f"Fixture not found: {FIXTURE_PATH}")

    svc = AudioFxChainService(media_service=mock_media_service)
    req = FxChainRequest(
        tenant_id="t1",
        env="dev",
        asset_id="asset_test",
        preset_id="tape_warmth",
        dry_wet=1.3,
        params_override={"hpf_hz": 10000, "sat": {"drive": 1.5}}
    )

    with patch("engines.audio_fx_chain.service.check_dependencies") as mock_check, \
         patch("engines.audio_fx_chain.service.subprocess.run", side_effect=_fake_subprocess_run):
        mock_check.return_value = _fake_dependencies(True)
        res = svc.apply_fx(req)

    assert res.meta["dry_wet"] == 1.0
    assert res.params_applied["hpf_hz"] == 4000.0
    assert res.params_applied["sat"]["drive"] == 1.0
    assert res.meta["knob_overrides"] == {"hpf_hz": 10000, "sat": {"drive": 1.5}}
    assert res.meta["backend_info"]["backend_type"] == "ffmpeg"


def test_apply_fx_missing_dependency(mock_media_service):
    svc = AudioFxChainService(media_service=mock_media_service)
    req = FxChainRequest(
        tenant_id="t1",
        env="dev",
        asset_id="asset_test",
        preset_id="clean_hit"
    )

    with patch("engines.audio_fx_chain.service.check_dependencies") as mock_check:
        mock_check.return_value = _fake_dependencies(False)
        with pytest.raises(DependencyMissingError):
            svc.apply_fx(req)


def test_apply_fx_invalid_preset(mock_media_service):
    svc = AudioFxChainService(media_service=mock_media_service)
    req = FxChainRequest(
        tenant_id="t1",
        env="dev",
        asset_id="asset_test",
        preset_id="clean_hit"
    )

    with patch("engines.audio_fx_chain.service.check_dependencies") as mock_check, \
         patch.dict("engines.audio_fx_chain.presets.FX_PRESETS", {}, clear=True):
        mock_check.return_value = _fake_dependencies(True)
        with pytest.raises(ValueError):
            svc.apply_fx(req)
