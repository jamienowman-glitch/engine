import pytest
from unittest.mock import MagicMock, patch

from engines.audio_hits.service import AudioHitsService
from engines.audio_hits.models import HitDetectRequest
from engines.audio_shared.health import DependencyInfo
from engines.media_v2.models import MediaAsset, DerivedArtifact

def test_detect_hits_basic():
    mock_media = MagicMock()
    # Mock Asset
    mock_media.get_asset.return_value = MediaAsset(
        id="asset_1", tenant_id="t1", env="dev", kind="audio", source_uri="/tmp/fake.wav", duration_ms=5000
    )
    # Mock Register
    def fake_reg(req):
        return DerivedArtifact(
            id=f"art_{req.start_ms}", 
            parent_asset_id=req.parent_asset_id,
            tenant_id=req.tenant_id, env=req.env,
            kind=req.kind, uri=req.uri,
            start_ms=req.start_ms, end_ms=req.end_ms,
            meta=req.meta
        )
    mock_media.register_artifact.side_effect = fake_reg
    
    service = AudioHitsService(media_service=mock_media)
    
    req = HitDetectRequest(
        tenant_id="t1", env="dev", asset_id="asset_1",
        min_peak_db=-30
    )
    
    with patch("engines.audio_hits.service.check_dependencies") as mock_check:
        mock_check.return_value = {
            "ffmpeg": DependencyInfo(True, "6.0", None),
            "ffprobe": DependencyInfo(True, "6.0", None),
            "demucs": DependencyInfo(True, "4.1", None),
            "librosa": DependencyInfo(False, None, "missing"),
        }
        res = service.detect_hits(req)
    
    assert len(res.events) == 5
    assert len(res.artifact_ids) == 5


def test_stub_respects_min_interval():
    """StubHitsBackend should honor min_interval_ms and skip closely spaced onsets."""
    mock_media = MagicMock()
    mock_media.get_asset.return_value = MediaAsset(
        id="asset_1", tenant_id="t1", env="dev", kind="audio", source_uri="/tmp/fake.wav", duration_ms=5000
    )
    def fake_reg(req):
        return DerivedArtifact(
            id=f"art_{req.start_ms}",
            parent_asset_id=req.parent_asset_id,
            tenant_id=req.tenant_id, env=req.env,
            kind=req.kind, uri=req.uri,
            start_ms=req.start_ms, end_ms=req.end_ms,
            meta=req.meta
        )
    mock_media.register_artifact.side_effect = fake_reg

    service = AudioHitsService(media_service=mock_media)
    # Use a larger min_interval_ms so the stub's dense onsets are thinned
    req = HitDetectRequest(
        tenant_id="t1", env="dev", asset_id="asset_1",
        min_peak_db=-30,
        min_interval_ms=1500
    )

    with patch("engines.audio_hits.service.check_dependencies") as mock_check:
        mock_check.return_value = {
            "ffmpeg": DependencyInfo(True, "6.0", None),
            "ffprobe": DependencyInfo(True, "6.0", None),
            "demucs": DependencyInfo(True, "4.1", None),
            "librosa": DependencyInfo(False, None, "missing"),
        }
        res = service.detect_hits(req)

    # Stub with min_interval_ms=1500 should yield fewer hits (thinned)
    assert len(res.events) < 5
    assert len(res.artifact_ids) == len(res.events)
    
    # Check first event
    evt0 = res.events[0]
    assert evt0.source_start_ms >= 0
    assert evt0.source_end_ms > evt0.source_start_ms
    
    # Check meta return
    assert res.meta["engine"] == "audio_hits_v2"
    backend_info = res.meta["backend_info"]
    assert backend_info["service"] == "audio_hits"
    assert backend_info["backend_type"] in ("stub", "librosa")
    assert "backend_version" in backend_info


def test_detect_hits_rejects_unknown_tenant():
    mock_media = MagicMock()
    mock_media.get_asset.return_value = MediaAsset(
        id="asset_1", tenant_id="t1", env="dev", kind="audio", source_uri="/tmp/fake.wav", duration_ms=1000
    )
    mock_media.register_artifact.return_value = DerivedArtifact(
        id="art", parent_asset_id="asset_1", tenant_id="t1", env="dev", kind="audio_hit", uri="/tmp/fake.wav",
        start_ms=0, end_ms=100, meta={}
    )

    service = AudioHitsService(media_service=mock_media)
    req = HitDetectRequest(
        tenant_id="t_unknown",
        env="dev",
        asset_id="asset_1",
        min_peak_db=-30
    )

    with patch("engines.audio_hits.service.check_dependencies") as mock_check:
        mock_check.return_value = {
            "ffmpeg": DependencyInfo(True, "6.0", None),
            "ffprobe": DependencyInfo(True, "6.0", None),
            "demucs": DependencyInfo(True, "4.1", None),
            "librosa": DependencyInfo(False, None, "missing"),
        }
        with pytest.raises(ValueError):
            service.detect_hits(req)


def test_detect_hits_stub_backend_when_librosa_missing():
    mock_media = MagicMock()
    mock_media.get_asset.return_value = MediaAsset(
        id="asset_1", tenant_id="t1", env="dev", kind="audio", source_uri="/tmp/fake.wav", duration_ms=1000
    )
    def fake_reg(req):
        return DerivedArtifact(
            id=f"art_{req.start_ms}",
            parent_asset_id=req.parent_asset_id,
            tenant_id=req.tenant_id,
            env=req.env,
            kind=req.kind,
            uri=req.uri,
            start_ms=req.start_ms,
            end_ms=req.end_ms,
            meta=req.meta,
        )
    mock_media.register_artifact.side_effect = fake_reg

    service = AudioHitsService(media_service=mock_media)
    req = HitDetectRequest(
        tenant_id="t1",
        env="dev",
        asset_id="asset_1",
        min_peak_db=-30,
    )

    with patch("engines.audio_hits.service.check_dependencies") as mock_check:
        mock_check.return_value = {
            "ffmpeg": DependencyInfo(True, "6.0", None),
            "ffprobe": DependencyInfo(True, "6.0", None),
            "demucs": DependencyInfo(True, "4.1", None),
            "librosa": DependencyInfo(False, None, "missing"),
        }
        res = service.detect_hits(req)

    assert res.meta["backend_info"]["backend_type"] == "stub"
