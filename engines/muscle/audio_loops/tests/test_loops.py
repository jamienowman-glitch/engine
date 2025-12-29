import pytest
from unittest.mock import MagicMock, patch

from engines.audio_loops.service import AudioLoopsService
from engines.audio_loops.models import LoopDetectRequest
from engines.audio_shared.health import DependencyInfo
from engines.media_v2.models import MediaAsset, DerivedArtifact

def _fake_dependencies(librosa_available: bool) -> dict[str, DependencyInfo]:
    return {
        "ffmpeg": DependencyInfo(True, "6.0", None),
        "ffprobe": DependencyInfo(True, "6.0", None),
        "demucs": DependencyInfo(True, "4.1", None),
        "librosa": DependencyInfo(librosa_available, "0.10.0" if librosa_available else None, None if librosa_available else "missing"),
    }


def test_detect_loops_basic():
    mock_media = MagicMock()
    # 20 sec audio
    mock_media.get_asset.return_value = MediaAsset(
        id="asset_1", tenant_id="t1", env="dev", kind="audio", source_uri="/tmp/fake.wav", duration_ms=20000
    )
    def fake_reg(req):
        return DerivedArtifact(
            id=f"loop_{req.start_ms}", 
            parent_asset_id=req.parent_asset_id,
            tenant_id=req.tenant_id, env=req.env,
            kind=req.kind, uri=req.uri,
            start_ms=req.start_ms, end_ms=req.end_ms,
            meta=req.meta
        )
    mock_media.register_artifact.side_effect = fake_reg
    
    service = AudioLoopsService(media_service=mock_media)
    
    req = LoopDetectRequest(
        tenant_id="t1", env="dev", asset_id="asset_1",
        target_bars=[2, 4]
    )
    
    with patch("engines.audio_loops.service.check_dependencies") as mock_check:
        mock_check.return_value = _fake_dependencies(False)
        res = service.detect_loops(req)
    
    # Expect 2 loops (2 bars, 4 bars)
    assert len(res.loops) == 2
    assert len(res.artifact_ids) == 2
    
    # Analyze first loop
    l1 = res.loops[0]
    assert l1.bpm == 120.0
    assert l1.loop_bars == 2
    # 2 bars at 120bpm = 4000ms
    assert (l1.end_ms - l1.start_ms) == 4000.0
    
    # Analyze second loop
    l2 = res.loops[1]
    assert l2.loop_bars == 4
    assert (l2.end_ms - l2.start_ms) == 8000.0
    
    backend_info = res.meta["backend_info"]
    assert backend_info["service"] == "audio_loops"
    assert backend_info["backend_type"] == "stub"
    assert res.meta["engine"] == "audio_loops_v2"


def test_detect_loops_rejects_unknown_tenant():
    mock_media = MagicMock()
    mock_media.get_asset.return_value = MediaAsset(
        id="asset_1", tenant_id="t1", env="dev", kind="audio", source_uri="/tmp/fake.wav", duration_ms=20000
    )
    mock_media.register_artifact.return_value = DerivedArtifact(
        id="loop_0", parent_asset_id="asset_1", tenant_id="t1", env="dev",
        kind="audio_loop", uri="/tmp/fake.wav", start_ms=0, end_ms=0, meta={}
    )
    service = AudioLoopsService(media_service=mock_media)
    req = LoopDetectRequest(
        tenant_id="t_unknown", env="dev", asset_id="asset_1"
    )

    with patch("engines.audio_loops.service.check_dependencies") as mock_check:
        mock_check.return_value = _fake_dependencies(False)
        with pytest.raises(ValueError):
            service.detect_loops(req)


def test_detect_loops_stub_health_metadata():
    mock_media = MagicMock()
    mock_media.get_asset.return_value = MediaAsset(
        id="asset_1", tenant_id="t1", env="dev", kind="audio", source_uri="/tmp/fake.wav", duration_ms=20000
    )
    mock_media.register_artifact.return_value = DerivedArtifact(
        id="loop_0", parent_asset_id="asset_1", tenant_id="t1", env="dev",
        kind="audio_loop", uri="/tmp/fake.wav", start_ms=0, end_ms=0, meta={}
    )
    service = AudioLoopsService(media_service=mock_media)
    req = LoopDetectRequest(tenant_id="t1", env="dev", asset_id="asset_1")
    with patch("engines.audio_loops.service.check_dependencies") as mock_check:
        mock_check.return_value = _fake_dependencies(False)
        res = service.detect_loops(req)

    assert res.meta["backend_info"]["backend_type"] == "stub"
