import os
import pytest
from unittest.mock import MagicMock, patch, mock_open
from engines.audio_hits.service import AudioHitsService
from engines.audio_hits.models import HitDetectRequest
from engines.media_v2.models import MediaAsset, DerivedArtifact

@patch("engines.audio_hits.service.get_media_service")
@patch("engines.audio_hits.service.GcsClient")
@patch("engines.audio_hits.service.shutil.which")
@patch("engines.audio_hits.service.subprocess.run")
@patch("engines.audio_hits.service.LibrosaHitsBackend")
@patch("engines.audio_hits.service.HAS_LIBROSA", True)
def test_detect_hits_real(mock_backend_cls, mock_run, mock_which, mock_gcs, mock_get_media):
    # Setup Mocks
    mock_media = mock_get_media.return_value
    mock_media.get_asset.return_value = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="audio", source_uri="gs://bucket/file.wav")
    
    # Mock GCS ensure local
    # We patch _ensure_local or mock GCS client properly?
    # Service calls self.gcs._client.bucket...
    # Too complex to mock GCS internals easily, let's mock _ensure_local if possible, or assume simple logic triggers.
    # Service Logic: if gs:// -> download.
    # Let's mock GCS client to avoid crash.
    mock_gcs_instance = mock_gcs.return_value
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_gcs_instance._client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    
    # Mock backend instance
    mock_backend = mock_backend_cls.return_value
    from engines.audio_hits.backend import OnsetResult
    # Return 2 hits
    mock_backend.detect.return_value = [
        OnsetResult(start_ms=100, end_ms=200, peak_db=-6),
        OnsetResult(start_ms=500, end_ms=600, peak_db=-3)
    ]
    
    # Mock upload return
    mock_media.register_upload.return_value = MediaAsset(id="a2", tenant_id="t1", env="dev", kind="audio", source_uri="gs://bucket/slice.wav")
    
    # Mock artifact register return
    mock_media.register_artifact.return_value = DerivedArtifact(
        id="h1", tenant_id="t1", env="dev", parent_asset_id="a1", kind="audio_hit", uri="gs://bucket/slice.wav"
    )
    
    # Mock ffmpeg existence
    mock_which.return_value = "/usr/bin/ffmpeg"
    
    # Mock subprocess success
    mock_run.return_value.returncode = 0
    
    # Mock file existence checks in Service
    # Service checks: os.path.exists(local_path)
    # We used tempfile path.
    with patch("engines.audio_hits.service.os.path.exists", return_value=True):
        # Also need to mock reading bytes from the sliced path
        with patch("engines.audio_hits.service.Path.read_bytes", return_value=b"FAKE_WAV_BYTES"):
             # Also allow unlink
            with patch("engines.audio_hits.service.Path.unlink", return_value=None):
                
                # Setup Service
                svc = AudioHitsService(media_service=mock_media)
                req = HitDetectRequest(tenant_id="t1", env="dev", asset_id="a1")
                
                res = svc.detect_hits(req)
                
                # Verify
                assert len(res.events) == 2
                assert len(res.artifact_ids) == 2
                assert res.meta["engine"] == "audio_hits_v2"
                
                # Check ensure_local called blob download
                mock_blob.download_to_filename.assert_called_once()
                
                # Check backend detect called
                mock_backend.detect.assert_called_once()
                
                # Check slicing (ffmpeg call)
                assert mock_run.call_count == 2 # 2 hits
                cmd = mock_run.call_args_list[0][0][0]
                assert cmd[0] == "ffmpeg"
                assert "-ss" in cmd
                assert "-t" in cmd
                
                # Check upload
                assert mock_media.register_upload.call_count == 2
                args = mock_media.register_upload.call_args[0] # args: (req, filename, content)
                assert args[2] == b"FAKE_WAV_BYTES"
                
                # Check artifact registration
                # Should have slice_asset_id in meta
                args_art = mock_media.register_artifact.call_args[0][0]
                assert args_art.kind == "audio_hit"
                assert "slice_asset_id" in args_art.meta
