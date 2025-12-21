from types import SimpleNamespace

import pytest
from unittest.mock import MagicMock, patch

from engines.audio_resample.service import AudioResampleService, ResampleRequest
from engines.audio_shared.health import DependencyInfo, DependencyMissingError
from engines.media_v2.models import MediaAsset, DerivedArtifact


def _fake_dependencies(ffmpeg_available: bool) -> dict[str, DependencyInfo]:
    return {
        "ffmpeg": DependencyInfo(ffmpeg_available, "6.1" if ffmpeg_available else None, None if ffmpeg_available else "missing"),
        "ffprobe": DependencyInfo(True, "6.1", None),
        "demucs": DependencyInfo(True, "4.1", None),
        "librosa": DependencyInfo(True, "0.10", None),
    }


def _fake_resample_run(cmd, check, stdout, stderr):
    return SimpleNamespace(returncode=0)

def test_resample_command_logic():
    mock_media = MagicMock()
    mock_media.get_artifact.return_value = DerivedArtifact(
        id="art_1", parent_asset_id="p1", tenant_id="t1", env="d", kind="audio_loop",
        uri="/tmp/loop.wav", meta={"bpm": 120.0}
    )
    
    with patch("engines.audio_resample.service.check_dependencies") as mock_check, \
         patch("engines.audio_resample.service.subprocess.run", side_effect=_fake_resample_run) as mock_run, \
         patch("engines.audio_resample.service.Path.read_bytes", return_value=b"fake_audio"):
        mock_check.return_value = _fake_dependencies(True)

        mock_media.register_upload.return_value = MediaAsset(
            id="a_new", tenant_id="t1", env="d", kind="audio", source_uri="/tmp/resamp.wav"
        )
        mock_media.register_artifact.return_value = DerivedArtifact(
            id="art_new", parent_asset_id="a_new", tenant_id="t1", env="d", kind="audio_resampled",
            uri="/tmp/resamp.wav"
        )
        
        svc = AudioResampleService(media_service=mock_media)
        
        req = ResampleRequest(
            tenant_id="t1", env="d", artifact_id="art_1",
            target_bpm=140.0
        )
        
        res = svc.resample_artifact(req)
        
        args, _ = mock_run.call_args
        cmd = args[0]
        
        assert "-af" in cmd
        filter_idx = cmd.index("-af") + 1
        f_str = cmd[filter_idx]
        assert "rubberband" in f_str
        assert "tempo=1.16" in f_str
        assert res.meta["quality_preset"] == "quality"
        assert res.meta["preserve_formants"] is False
        assert res.meta["resample_params"]["quality_preset"] == "quality"
        assert res.meta["backend_info"]["backend_type"] == "ffmpeg"

def test_resample_pitch_only():
    mock_media = MagicMock()
    mock_media.get_artifact.return_value = DerivedArtifact(
        id="art_1", parent_asset_id="p1", tenant_id="t1", env="d", kind="audio_loop",
        uri="/tmp/loop.wav", meta={"bpm": 120.0}
    )
    
    with patch("engines.audio_resample.service.check_dependencies") as mock_check, \
         patch("engines.audio_resample.service.subprocess.run", side_effect=_fake_resample_run) as mock_run, \
         patch("engines.audio_resample.service.Path.read_bytes", return_value=b"fake_audio"):

        mock_check.return_value = _fake_dependencies(True)
        mock_media.register_upload.return_value = MediaAsset(
            id="a_new", tenant_id="t1", env="d", kind="audio", source_uri="/tmp/resamp.wav"
        )
        mock_media.register_artifact.return_value = DerivedArtifact(
            id="art_new", parent_asset_id="a_new", tenant_id="t1", env="d", kind="audio_resampled",
            uri="/tmp/resamp.wav"
        )

        svc = AudioResampleService(media_service=mock_media)

        req = ResampleRequest(
            tenant_id="t1", env="d", artifact_id="art_1",
            pitch_semitones=2.0
        )
        res = svc.resample_artifact(req)

        args, _ = mock_run.call_args
        cmd = args[0]
        f_str = cmd[cmd.index("-af") + 1]
        assert "pitch=2.0" in f_str
        assert res.meta["resample_params"]["pitch_semitones"] == 2.0
        assert res.meta["backend_info"]["backend_type"] == "ffmpeg"


def test_resample_preserve_formants_flag():
    mock_media = MagicMock()
    mock_media.get_artifact.return_value = DerivedArtifact(
        id="art_1", parent_asset_id="p1", tenant_id="t1", env="d", kind="audio_loop",
        uri="/tmp/loop.wav", meta={"bpm": 118.0}
    )

    with patch("engines.audio_resample.service.check_dependencies") as mock_check, \
         patch("engines.audio_resample.service.subprocess.run", side_effect=_fake_resample_run) as mock_run, \
         patch("engines.audio_resample.service.Path.read_bytes", return_value=b"fake_audio"):

        mock_check.return_value = _fake_dependencies(True)
        mock_media.register_upload.return_value = MediaAsset(
            id="a_new", tenant_id="t1", env="d", kind="audio", source_uri="/tmp/resamp.wav"
        )
        mock_media.register_artifact.return_value = DerivedArtifact(
            id="art_new", parent_asset_id="a_new", tenant_id="t1", env="d", kind="audio_resampled",
            uri="/tmp/resamp.wav"
        )

        svc = AudioResampleService(media_service=mock_media)
        req = ResampleRequest(
            tenant_id="t1", env="d", artifact_id="art_1",
            target_bpm=130.0, quality_preset="draft", preserve_formants=True
        )
        res = svc.resample_artifact(req)

        args, _ = mock_run.call_args
        cmd = args[0]
        f_str = cmd[cmd.index("-af") + 1]
        assert "formant=1" in f_str
        assert res.meta["quality_preset"] == "draft"
        assert res.meta["preserve_formants"] is True
        assert res.meta["backend_info"]["backend_type"] == "ffmpeg"


def test_no_resample_parameters_returns_original():
    mock_media = MagicMock()
    mock_media.get_artifact.return_value = DerivedArtifact(
        id="art_no", parent_asset_id="p1", tenant_id="t1", env="d", kind="audio_loop",
        uri="/tmp/loop.wav", meta={"bpm": 120.0, "end_ms": 4000.0, "start_ms": 0.0}
    )
    svc = AudioResampleService(media_service=mock_media)
    req = ResampleRequest(tenant_id="t1", env="d", artifact_id="art_no")

    with patch("engines.audio_resample.service.check_dependencies") as mock_check:
        mock_check.return_value = _fake_dependencies(True)
        res = svc.resample_artifact(req)
        assert res.artifact_id == "art_no"
        assert res.meta["returned_original"] is True
        assert res.meta["resample_params"]["quality_preset"] == "quality"
        assert res.meta["reason"].startswith("no tempo")


def test_quality_preset_normalization():
    mock_media = MagicMock()
    mock_media.get_artifact.return_value = DerivedArtifact(
        id="art_quality", parent_asset_id="p1", tenant_id="t1", env="d", kind="audio_loop",
        uri="/tmp/loop.wav", meta={"bpm": 130.0}
    )
    with patch("engines.audio_resample.service.check_dependencies") as mock_check, \
         patch("engines.audio_resample.service.subprocess.run", side_effect=_fake_resample_run), \
         patch("engines.audio_resample.service.Path.read_bytes", return_value=b"fake_audio"):
        mock_check.return_value = _fake_dependencies(True)
        mock_media.register_upload.return_value = MediaAsset(
            id="a_new", tenant_id="t1", env="d", kind="audio", source_uri="/tmp/resamp.wav"
        )
        mock_media.register_artifact.return_value = DerivedArtifact(
            id="art_new", parent_asset_id="a_new", tenant_id="t1", env="d", kind="audio_resampled",
            uri="/tmp/resamp.wav"
        )
        svc = AudioResampleService(media_service=mock_media)
        req = ResampleRequest(
            tenant_id="t1", env="d", artifact_id="art_quality",
            target_bpm=140.0, quality_preset="High"
        )
        res = svc.resample_artifact(req)
        assert res.meta["quality_preset"] == "quality"
        assert res.meta["resample_params"]["quality_preset"] == "quality"
        args, _ = mock_media.register_upload.call_args
        # ensure command includes quality args from soxr
        # actual command built inside service; we rely on no exception
        assert res.meta["backend_info"]["backend_type"] == "ffmpeg"


def test_pitch_clamps_to_limit():
    mock_media = MagicMock()
    mock_media.get_artifact.return_value = DerivedArtifact(
        id="art_extreme", parent_asset_id="p1", tenant_id="t1", env="d", kind="audio_loop",
        uri="/tmp/loop.wav", meta={"bpm": 120.0}
    )
    with patch("engines.audio_resample.service.check_dependencies") as mock_check, \
         patch("engines.audio_resample.service.subprocess.run", side_effect=_fake_resample_run), \
         patch("engines.audio_resample.service.Path.read_bytes", return_value=b"fake_audio"):
        mock_check.return_value = _fake_dependencies(True)
        mock_media.register_upload.return_value = MediaAsset(
            id="a_new", tenant_id="t1", env="d", kind="audio", source_uri="/tmp/resamp.wav"
        )
        mock_media.register_artifact.return_value = DerivedArtifact(
            id="art_new", parent_asset_id="a_new", tenant_id="t1", env="d", kind="audio_resampled",
            uri="/tmp/resamp.wav"
        )
        svc = AudioResampleService(media_service=mock_media)
        req = ResampleRequest(
            tenant_id="t1", env="d", artifact_id="art_extreme",
            pitch_semitones=20.0
        )
        res = svc.resample_artifact(req)
        assert res.meta["resample_params"]["pitch_semitones"] == 12.0


def test_resample_missing_dependency():
    mock_media = MagicMock()
    mock_media.get_artifact.return_value = DerivedArtifact(
        id="art_1", parent_asset_id="p1", tenant_id="t1", env="d", kind="audio_loop",
        uri="/tmp/loop.wav", meta={"bpm": 118.0}
    )
    svc = AudioResampleService(media_service=mock_media)
    req = ResampleRequest(
        tenant_id="t1", env="d", artifact_id="art_1", target_bpm=130.0
    )

    with patch("engines.audio_resample.service.check_dependencies") as mock_check:
        mock_check.return_value = _fake_dependencies(False)
        with pytest.raises(DependencyMissingError):
            svc.resample_artifact(req)
