
import pytest
from unittest.mock import MagicMock, patch
from engines.video_multicam.service import MultiCamService, ALIGNMENT_CACHE_VERSION
from engines.video_multicam.models import (
    MultiCamSession, MultiCamTrackSpec, MultiCamAlignRequest
)

@pytest.fixture
def mock_media_service():
    return MagicMock()

@pytest.fixture
def mock_timeline_service():
    return MagicMock()

@pytest.fixture
def mock_backend():
    return MagicMock()

@pytest.fixture
def service(mock_media_service, mock_timeline_service, mock_backend):
    # Initialize with mocked dependencies
    svc = MultiCamService(
        media_service=mock_media_service,
        timeline_service=mock_timeline_service,
        align_backend=mock_backend
    )
    # Stub GCS
    svc.gcs = None
    return svc

def test_align_session_tenant_mismatch(service):
    session = MultiCamSession(
        id="sess_1", tenant_id="t1", env="dev", name="S1",
        tracks=[MultiCamTrackSpec(asset_id="a1")]
    )
    service.repo.create(session)
    
    req = MultiCamAlignRequest(
        tenant_id="t2", env="dev", session_id="sess_1"
    )
    with pytest.raises(ValueError, match="Access Denied: Tenant mismatch"):
        service.align_session(req)

def test_align_session_env_mismatch(service):
    session = MultiCamSession(
        id="sess_1", tenant_id="t1", env="dev", name="S1",
        tracks=[MultiCamTrackSpec(asset_id="a1")]
    )
    service.repo.create(session)
    
    req = MultiCamAlignRequest(
        tenant_id="t1", env="prod", session_id="sess_1"
    )
    with pytest.raises(ValueError, match="Access Denied: Environment mismatch"):
        service.align_session(req)

def test_align_session_success(service, mock_backend, mock_media_service):
    # Setup session
    session = MultiCamSession(
        id="sess_ok", tenant_id="t1", env="dev", name="S1",
        tracks=[
            MultiCamTrackSpec(asset_id="cam1", role="primary"),
            MultiCamTrackSpec(asset_id="cam2", role="secondary")
        ],
        base_asset_id="cam1"
    )
    service.repo.create(session)
    
    # Mock assets
    mock_media_service.get_asset.return_value = MagicMock(kind="video", source_uri="/tmp/cam.mp4")
    # Mock backend return
    mock_backend.calculate_offset.return_value = (500.0, 0.95)
    
    # Force _ensure_local to return the uri
    service._ensure_local = lambda x: x
    # Force _waveform_samples_for_asset to return None so we hit backend
    service._waveform_samples_for_asset = lambda x: None

    req = MultiCamAlignRequest(
        tenant_id="t1", env="dev", session_id="sess_ok",
        alignment_method="waveform_cross_correlation",
        max_search_ms=5000
    )
    
    result = service.align_session(req)
    
    assert result.offsets_ms["cam1"] == 0
    assert result.offsets_ms["cam2"] == 500
    assert result.meta.get("confidences", {}).get("cam2") == 0.95
    assert result.meta["alignment_version"] == ALIGNMENT_CACHE_VERSION
    
    # Verify session update
    updated_session = service.get_session("sess_ok")
    assert updated_session.tracks[1].offset_ms == 500
    assert updated_session.meta["last_alignment"]["confidences"]["cam2"] == 0.95


def test_align_session_cache_hit(service, mock_backend, mock_media_service):
    # Setup session with pre-filled cache (V04 structure)
    cache_key = f"waveform_cross_correlation:5000:{ALIGNMENT_CACHE_VERSION}"
    session = MultiCamSession(
        id="sess_cache", tenant_id="t1", env="dev", name="S1",
        tracks=[
            MultiCamTrackSpec(asset_id="cam1"),
            MultiCamTrackSpec(asset_id="cam2")
        ],
        base_asset_id="cam1",
        meta={
            "alignment_cache": {
                cache_key: {
                    "offsets": {"cam1": 0, "cam2": 1234},
                    "confidences": {"cam1": 1.0, "cam2": 0.88}
                }
            },
            "last_alignment": {
                "method": "waveform_cross_correlation",
                "offsets": {"cam1": 0, "cam2": 1234},
                "confidences": {"cam1": 1.0, "cam2": 0.88}
            }
        }
    )
    service.repo.create(session)

    req = MultiCamAlignRequest(
        tenant_id="t1", env="dev", session_id="sess_cache",
        alignment_method="waveform_cross_correlation",
        max_search_ms=5000
    )
    
    result = service.align_session(req)
    
    assert result.offsets_ms["cam2"] == 1234
    assert result.meta["cache_hit"] is True
    # Should retrieve confidence from cache
    assert result.meta.get("confidences", {}).get("cam2") == 0.88
    
    # Backend should NOT be called
    mock_backend.calculate_offset.assert_not_called()
