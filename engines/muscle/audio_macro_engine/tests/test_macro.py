import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from unittest.mock import MagicMock, patch

from engines.audio_macro_engine.compiler import compile_macro_to_ffmpeg
from engines.audio_macro_engine.presets import MACRO_DEFINITIONS
from engines.audio_macro_engine.service import AudioMacroEngineService, MacroRequest
from engines.audio_shared.health import DependencyInfo, DependencyMissingError
from engines.media_v2.models import DerivedArtifact, MediaAsset


def _fake_dependencies(ffmpeg_available: bool) -> dict[str, DependencyInfo]:
    return {
        "ffmpeg": DependencyInfo(ffmpeg_available, "6.1" if ffmpeg_available else None, None if ffmpeg_available else "missing"),
        "ffprobe": DependencyInfo(True, "6.1", None),
        "demucs": DependencyInfo(True, "4.1", None),
        "librosa": DependencyInfo(True, "0.10", None),
    }


def _fake_macro_run(cmd, check, stdout, stderr):
    out_path = Path(cmd[-1])
    out_path.write_bytes(b"macro")
    return SimpleNamespace(returncode=0)

def test_compiler_reverse_swell():
    macro = MACRO_DEFINITIONS["reverse_swell"]
    # Nodes: Reverse, Reverb, Limiter
    # [0:a]areverse[n0];[n0]aecho=...[n1];[n1]alimiter=...[n2]
    
    flt, out = compile_macro_to_ffmpeg(macro)
    
    assert "areverse" in flt
    assert "aecho" in flt
    assert "alimiter" in flt
    assert "[0:a]" in flt # Input
    assert out == "[n2]" # 3 nodes -> n0, n1, n2

def test_execute_macro_service():
    mock_media = MagicMock()
    mock_media.get_artifact.return_value = DerivedArtifact(
        id="a1", parent_asset_id="p", tenant_id="t", env="d", kind="audio_loop", uri="/tmp/in.wav"
    )
    
    mock_media.register_upload.return_value = MediaAsset(id="up1", tenant_id="t", env="d", kind="audio", source_uri="/tmp/out.wav")
    
    mock_media.register_artifact.return_value = DerivedArtifact(
        id="res1", parent_asset_id="up1", tenant_id="t", env="d", kind="audio_macro", uri="/tmp/out.wav"
    )
    
    with patch("engines.audio_macro_engine.service.check_dependencies") as mock_check, \
         patch("engines.audio_macro_engine.service.subprocess.run", side_effect=_fake_macro_run) as mock_run:
        mock_check.return_value = _fake_dependencies(True)
        svc = AudioMacroEngineService(media_service=mock_media)
        req = MacroRequest(
            tenant_id="t", env="d", 
            artifact_id="a1", 
            macro_id="reverse_swell"
        )
        res = svc.execute_macro(req)

        assert res.artifact_id == "res1"
        
        # Verify Command
        args, _ = mock_run.call_args
        cmd = args[0]
        
        # Should have filter complex
        assert "-filter_complex" in cmd
        idx = cmd.index("-filter_complex")
        flt = cmd[idx+1]
        assert "areverse" in flt
    assert res.meta["backend_info"]["backend_type"] == "ffmpeg"

def test_macro_override_logging():
    mock_media = MagicMock()
    mock_media.get_artifact.return_value = DerivedArtifact(
        id="a1", parent_asset_id="p", tenant_id="t", env="d", kind="audio_loop", uri="/tmp/in.wav"
    )
    mock_media.register_upload.return_value = MediaAsset(id="up1", tenant_id="t", env="d", kind="audio", source_uri="/tmp/out.wav")
    def fake_artifact(req):
        return DerivedArtifact(
            id="res2", parent_asset_id=req.parent_asset_id, tenant_id=req.tenant_id,
            env=req.env, kind=req.kind, uri=req.uri, meta=req.meta
        )
    mock_media.register_artifact.side_effect = fake_artifact

    with patch("engines.audio_macro_engine.service.check_dependencies") as mock_check, \
         patch("engines.audio_macro_engine.service.subprocess.run", side_effect=_fake_macro_run) as mock_run, \
         patch("engines.audio_macro_engine.service.logger") as mock_logger:

        mock_check.return_value = _fake_dependencies(True)
        svc = AudioMacroEngineService(media_service=mock_media)
        req = MacroRequest(
            tenant_id="t", env="d",
            artifact_id="a1",
            macro_id="sparkle_tap",
            knob_overrides={"0.drive": 200, "foo": 1}
        )

        res = svc.execute_macro(req)

        # Sanitized override should clamp to 100 and drop unknown key
        assert res.meta["knob_overrides"]["0.drive"] == 100.0
        assert "foo" not in res.meta["knob_overrides"]
        mock_logger.info.assert_called()
        mock_logger.warning.assert_called()
    assert res.meta["backend_info"]["backend_type"] == "ffmpeg"


def test_macro_missing_ffmpeg():
    mock_media = MagicMock()
    mock_media.get_artifact.return_value = DerivedArtifact(
        id="a1", parent_asset_id="p", tenant_id="t", env="d", kind="audio_loop", uri="/tmp/in.wav"
    )
    svc = AudioMacroEngineService(media_service=mock_media)
    req = MacroRequest(tenant_id="t", env="d", artifact_id="a1", macro_id="reverse_swell")

    with patch("engines.audio_macro_engine.service.check_dependencies") as mock_check:
        mock_check.return_value = _fake_dependencies(False)
        with pytest.raises(DependencyMissingError):
            svc.execute_macro(req)
