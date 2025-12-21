import pytest
import json
from unittest.mock import MagicMock, patch
from engines.media_integrity.service import MediaIntegrityService
from engines.media_v2.models import MediaAsset

@patch("engines.media_integrity.service.get_media_service")
@patch("subprocess.run")
def test_check_asset_integrity(mock_subprocess, mock_ms_getter):
    mock_ms = mock_ms_getter.return_value
    
    # Mock Asset
    mock_ms.get_asset.return_value = MediaAsset(
        id="a1", tenant_id="t1", env="dev", kind="video", source_uri="/tmp/video.mp4"
    )
    
    # Mock ffprobe output
    mock_output = {
        "format": {"duration": "10.5"},
        "streams": [
            {
                "index": 0,
                "codec_type": "video",
                "width": 1920,
                "height": 1080,
                "color_space": "bt709"
            },
            {
                "index": 1,
                "codec_type": "audio"
            }
        ]
    }
    
    mock_subprocess.return_value.stdout = json.dumps(mock_output)
    mock_subprocess.return_value.returncode = 0
    
    svc = MediaIntegrityService(media_service=mock_ms)
    report = svc.check_asset("a1")
    
    assert report is not None
    assert report.status == "OK"
    assert len(report.streams) == 2
    assert report.streams[0].width == 1920
    assert report.streams[0].color_space == "bt709"

    # Test Corrupt logic is in a separate test (test_check_asset_corrupt)
    # Ensure current test finishes cleanly
    assert report.status == "OK"

@patch("engines.media_integrity.service.get_media_service")
@patch("subprocess.run")
def test_check_asset_corrupt(mock_subprocess, mock_ms_getter):
    mock_ms = mock_ms_getter.return_value
    mock_ms.get_asset.return_value = MediaAsset(id="a2", tenant_id="t1", env="dev", kind="video", source_uri="/tmp/bad.mp4")
    
    # Mock invalid JSON
    mock_subprocess.return_value.stdout = "Garbage"
    
    svc = MediaIntegrityService(media_service=mock_ms)
    report = svc.check_asset("a2")
    
    assert report.status == "CORRUPT"
