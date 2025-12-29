import pytest
from unittest.mock import MagicMock
from engines.audio_to_video_origin.service import AudioToVideoOriginService, ShotListRequest
from engines.audio_semantic_timeline.models import AudioEvent, AudioSemanticTimelineSummary, AudioSemanticTimelineGetResponse
from engines.audio_semantic_timeline.service import set_audio_semantic_service
from engines.audio_timeline.service import AudioTimelineService
from engines.media_v2.models import DerivedArtifact, MediaAsset

def test_generate_shot_list():
    mock_media = MagicMock()
    
    # Mock Artifacts
    # Art1: Derived from "video_source_1" starting at 10s (10000ms)
    def get_art(id):
        if id == "art1":
            return DerivedArtifact(
                id="art1", parent_asset_id="p", tenant_id="t", env="d", kind="audio_loop", uri="u",
                meta={"source_asset_id": "vid1", "source_start_ms": 10000.0}
            )
        return None
    mock_media.get_artifact.side_effect = get_art
    def list_artifacts_for_asset(asset_id):
        if asset_id == "vid1":
            return [
                DerivedArtifact(
                    id="sem1",
                    parent_asset_id="vid1",
                    tenant_id="t",
                    env="d",
                    kind="audio_semantic_timeline",
                    uri="mem://sem",
                    meta={
                        "semantic_version": "sem_v1",
                        "audio_semantic_cache_key": "cache_1",
                        "backend_version": "sem_v1",
                        "backend_type": "stub",
                        "backend_info": {},
                        "model_used": "stub_model",
                    },
                )
            ]
        return []
    mock_media.list_artifacts_for_asset.side_effect = list_artifacts_for_asset
    
    # Mock Upload/Register for Shotlist
    mock_media.register_upload.return_value = MediaAsset(id="sl_asset", tenant_id="t", env="d", kind="other", source_uri="sl_uri")
    
    summary = AudioSemanticTimelineSummary(
        asset_id="vid1",
        duration_ms=60000,
        events=[AudioEvent(kind="speech", start_ms=100, end_ms=500)],
        beats=[],
        meta={},
    )

    class SemanticStubService:
        def get_timeline(self, artifact_id: str):
            return AudioSemanticTimelineGetResponse(
                artifact_id=artifact_id,
                uri="mem://semantic",
                summary=summary,
                artifact_meta={"semantic_version": "sem_v1", "audio_semantic_cache_key": "cache_1"},
            )

    set_audio_semantic_service(SemanticStubService())

    svc = AudioToVideoOriginService(media_service=mock_media)
    tl_svc = AudioTimelineService()
    
    # Build Sequence
    seq = tl_svc.create_sequence("t", "d")
    t1 = tl_svc.add_track(seq, "VideoSync")
    
    # Clip 1: Uses Art1. Placed at 0ms. Duration 2000ms. Source Offset 500ms.
    # Expected Shot: Source Vid1. Range: 10000+500+semantic_offset -> 10000+500+2000+semantic_offset
    tl_svc.add_clip(t1, start_ms=0, artifact_id="art1", duration_ms=2000, source_offset_ms=500.0)
    
    # Clip 2: Uses Raw Asset "vid2". Placed at 3000ms. No meta offset.
    tl_svc.add_clip(t1, start_ms=3000, asset_id="vid2", duration_ms=1000)
    
    req = ShotListRequest(tenant_id="t", env="d", sequence=seq)
    res = svc.generate_shot_list(req)
    
    assert len(res.shots) == 2
    assert res.meta["count"] == 2
    assert res.meta["semantic_cache_key"] == "cache_1"
    assert res.meta["semantic_version"] == "sem_v1"
    
    # Verify Shot 1
    s1 = res.shots[0]
    assert s1.source_asset_id == "vid1"
    assert s1.source_start_ms == 10600.0  # +semantic offset (100ms)
    assert s1.source_end_ms == 12600.0
    assert s1.target_start_ms == 0.0
    assert s1.meta["semantic_version"] == "sem_v1"
    assert s1.meta["semantic_offset_ms"] == 100
    assert s1.meta["semantic_cache_key"] == "cache_1"
    
    # Verify Shot 2
    s2 = res.shots[1]
    assert s2.source_asset_id == "vid2"
    assert s2.source_start_ms == 0.0 # Raw asset, base 0 + offset 0
    assert s2.target_start_ms == 3000.0


def test_generate_shot_list_without_semantics(monkeypatch):
    mock_media = MagicMock()
    mock_media.list_artifacts_for_asset.return_value = []
    mock_media.register_upload.return_value = MediaAsset(
        id="sl_asset_missing",
        tenant_id="t",
        env="d",
        kind="other",
        source_uri="shot_missing",
    )
    mock_media.register_artifact.return_value = DerivedArtifact(
        id="sl_art_missing",
        parent_asset_id="sl_asset_missing",
        tenant_id="t",
        env="d",
        kind="video_shot_list",
        uri="shot_missing",
        meta={},
    )
    monkeypatch.setattr(
        "engines.audio_to_video_origin.service.get_audio_semantic_service",
        lambda: MagicMock(get_timeline=MagicMock()),
    )
    svc = AudioToVideoOriginService(media_service=mock_media)
    tl_svc = AudioTimelineService()
    seq = tl_svc.create_sequence("t", "d")
    t1 = tl_svc.add_track(seq, "Video Sync")
    tl_svc.add_clip(t1, start_ms=0, asset_id="raw_asset", duration_ms=1500)

    req = ShotListRequest(tenant_id="t", env="d", sequence=seq)
    res = svc.generate_shot_list(req)
    assert len(res.shots) == 1
    assert res.meta == {"count": 1}

    shot = res.shots[0]
    assert shot.source_asset_id == "raw_asset"
    assert shot.source_start_ms == 0.0
    assert shot.source_end_ms == 1500.0
    assert shot.meta["semantic_version"] is None
    assert shot.meta["semantic_cache_key"] is None
    assert shot.meta["semantic_offset_ms"] == 0.0
