import os
import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from engines.audio_loops.service import AudioLoopsService
from engines.audio_loops.models import LoopDetectRequest
from engines.media_v2.models import MediaAsset, DerivedArtifact

@patch("engines.audio_loops.service.get_media_service")
@patch("engines.audio_loops.service.GcsClient")
@patch("engines.audio_loops.service.shutil.which")
@patch("engines.audio_loops.service.subprocess.run")
@patch("engines.audio_loops.service.LibrosaLoopsBackend")
@patch("engines.audio_loops.service.HAS_LIBROSA", True)
def test_detect_loops_real(mock_backend_cls, mock_run, mock_which, mock_gcs, mock_get_media):
    # Setup Mocks
    mock_media = mock_get_media.return_value
    mock_media.get_asset.return_value = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="audio", source_uri="gs://bucket/loop.wav")
    
    # Mock GCS ensure local
    mock_gcs_instance = mock_gcs.return_value
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_gcs_instance._client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    
    # Mock backend instance
    mock_backend = mock_backend_cls.return_value
    from engines.audio_loops.backend import LoopCandidate
    mock_backend.detect.return_value = [
        LoopCandidate(start_ms=1000, end_ms=5000, bpm=120.0, loop_bars=2, confidence=0.9),
    ]
    
    # Mock upload return
    mock_media.register_upload.return_value = MediaAsset(id="a2", tenant_id="t1", env="dev", kind="audio", source_uri="gs://bucket/slice.wav")
    
    # Mock artifact register return
    mock_media.register_artifact.return_value = DerivedArtifact(
        id="l1", tenant_id="t1", env="dev", parent_asset_id="a1", kind="audio_loop", uri="gs://bucket/slice.wav"
    )
    
    # Mock ffmpeg existence
    mock_which.return_value = "/usr/bin/ffmpeg"
    mock_run.return_value.returncode = 0
    
    with patch("engines.audio_loops.service.os.path.exists", return_value=True):
        with patch("engines.audio_loops.service.Path.read_bytes", return_value=b"FAKE_LOOP_BYTES"):
            with patch("engines.audio_loops.service.Path.unlink", return_value=None):
                
                # Setup Service
                svc = AudioLoopsService(media_service=mock_media)
                req = LoopDetectRequest(tenant_id="t1", env="dev", asset_id="a1", target_bars=[2])
                
                res = svc.detect_loops(req)
                
                # Verify
                assert len(res.loops) == 1
                assert len(res.artifact_ids) == 1
                assert res.meta["engine"] == "audio_loops_v2"
                
                mock_backend.detect.assert_called_once()
                
                # Check slicing
                assert mock_run.call_count == 1
                cmd = mock_run.call_args_list[0][0][0]
                assert "ffmpeg" in cmd
                
                # Check upload used dummy source_uri
                assert mock_media.register_upload.call_count == 1
                args = mock_media.register_upload.call_args[0]
                assert args[0].source_uri == "pending"

