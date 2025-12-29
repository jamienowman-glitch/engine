import os
from unittest.mock import MagicMock, patch

import pytest

from engines.audio_separation.service import AudioSeparationService, SeparationRequest
from engines.audio_shared.health import DependencyInfo
from engines.media_v2.models import DerivedArtifact, MediaAsset


def _fake_dependencies(demucs_available: bool) -> dict[str, DependencyInfo]:
    return {
        "ffmpeg": DependencyInfo(True, "6.1", None),
        "ffprobe": DependencyInfo(True, "6.1", None),
        "demucs": DependencyInfo(demucs_available, "4.1" if demucs_available else None, None if demucs_available else "missing"),
        "librosa": DependencyInfo(True, "0.10", None),
    }

def test_separation_flow():
    mock_media = MagicMock()
    mock_media.get_artifact.return_value = DerivedArtifact(
        id="a1", parent_asset_id="p", tenant_id="t", env="d", kind="audio_loop", uri="/tmp/mix.wav"
    )
    
    def register_upload(req, fname, bytes):
        return MediaAsset(id=f"asset_{req.tags[-1]}", tenant_id="t", env="d", kind="audio", source_uri=f"uri_{req.tags[-1]}")
    mock_media.register_upload.side_effect = register_upload
    
    def register_artifact(req):
        return DerivedArtifact(
            id=f"art_{req.kind}", parent_asset_id=req.parent_asset_id, tenant_id="t", env="d", kind=req.kind, uri=req.uri, meta=req.meta
        )
    mock_media.register_artifact.side_effect = register_artifact
    
    with patch("engines.audio_separation.service.check_dependencies") as mock_check, \
         patch("engines.audio_separation.service.run_demucs_separation") as mock_backend, \
         patch("pathlib.Path.read_bytes", return_value=b"fake_audio"):
        mock_check.return_value = _fake_dependencies(True)
        mock_backend.return_value = {
            "drums": "/tmp/out/drums.wav",
            "bass": "/tmp/out/bass.wav"
        }
        
        svc = AudioSeparationService(media_service=mock_media)
        req = SeparationRequest(tenant_id="t", env="d", artifact_id="a1")
        
        res = svc.separate_audio(req)
        
        assert "drums" in res.stems
        assert "bass" in res.stems
        
        assert "audio_stem_drum" in res.stems["drums"]
        assert "audio_stem_bass" in res.stems["bass"]

        mock_backend.assert_called_once()
        args = mock_backend.call_args
        assert args[0][0] == "/tmp/mix.wav"
        assert res.meta["backend_info"]["backend_type"] == "demucs"


def test_separation_stub_fallback():
    mock_media = MagicMock()
    mock_media.get_artifact.return_value = DerivedArtifact(
        id="a1", parent_asset_id="p", tenant_id="t", env="d", kind="audio_loop", uri="/tmp/mix.wav"
    )
    mock_media.register_upload.return_value = MediaAsset(id="asset_stub", tenant_id="t", env="d", kind="audio", source_uri="/tmp/mix.wav")
    mock_media.register_artifact.return_value = DerivedArtifact(
        id="art_audio_stem_drum", parent_asset_id="asset_stub", tenant_id="t", env="d", kind="audio_stem_drum", uri="/tmp/mix.wav"
    )

    with patch("engines.audio_separation.service.check_dependencies") as mock_check, \
         patch("engines.audio_separation.service.run_demucs_separation") as mock_backend, \
         patch("pathlib.Path.read_bytes", return_value=b"fake_audio"):
        mock_check.return_value = _fake_dependencies(False)

        svc = AudioSeparationService(media_service=mock_media)
        req = SeparationRequest(tenant_id="t", env="d", artifact_id="a1")

        res = svc.separate_audio(req)

        mock_backend.assert_not_called()
        assert res.meta["backend_info"]["backend_type"] == "stub"
        assert res.meta["runtime_seconds"] == 0.0
