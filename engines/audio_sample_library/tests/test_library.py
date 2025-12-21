from unittest.mock import MagicMock
from engines.audio_sample_library.service import AudioSampleLibraryService
from engines.audio_sample_library.models import SampleLibraryQuery
from engines.media_v2.models import DerivedArtifact

def test_query_samples_filters():
    mock_media = MagicMock()
    
    # Mock Data: 1 hit, 1 loop, 1 phrase
    results = [
        DerivedArtifact(id="h1", parent_asset_id="a", tenant_id="t", env="d", kind="audio_hit", uri="u", start_ms=0, end_ms=100, meta={"peak_db": -5, "quality_score": 0.92, "role": "anchor"}),
        DerivedArtifact(id="l1", parent_asset_id="a", tenant_id="t", env="d", kind="audio_loop", uri="u", start_ms=0, end_ms=4000, meta={"bpm": 120, "loop_bars": 2}),
        DerivedArtifact(id="p1", parent_asset_id="a", tenant_id="t", env="d", kind="audio_phrase", uri="u", start_ms=0, end_ms=1000, meta={"transcript": "Yo"}),
    ]
    
    # Mock list_artifacts call
    mock_media.list_artifacts.return_value = results
    
    service = AudioSampleLibraryService(media_service=mock_media)
    
    # Test 1: Fetch all loops
    q1 = SampleLibraryQuery(tenant_id="t", env="d", kind="audio_loop")
    res1 = service.query_samples(q1)
    
    # media_service.list_artifacts was called?
    assert mock_media.list_artifacts.called
    
    # Should only match l1
    assert len(res1.samples) == 1
    assert res1.samples[0].artifact_id == "l1"
    assert res1.samples[0].bpm == 120
    
    # Test 2: BPM Filter (match)
    q2 = SampleLibraryQuery(tenant_id="t", env="d", kind="audio_loop", min_bpm=110, max_bpm=130)
    res2 = service.query_samples(q2)
    assert len(res2.samples) == 1

    # Test 3: BPM Filter (no match)
    q3 = SampleLibraryQuery(tenant_id="t", env="d", kind="audio_loop", min_bpm=130)
    res3 = service.query_samples(q3)
    assert len(res3.samples) == 0

    # Test 4: Pagination
    mock_media.list_artifacts.return_value = results * 10 # 30 items
    q4 = SampleLibraryQuery(tenant_id="t", env="d", limit=5)
    res4 = service.query_samples(q4)
    assert len(res4.samples) == 5

    # Test 5: Quality filter
    mock_media.list_artifacts.return_value = results
    q5 = SampleLibraryQuery(tenant_id="t", env="d", kind="audio_hit", min_quality_score=0.9)
    res5 = service.query_samples(q5)
    assert len(res5.samples) == 1
    assert res5.samples[0].quality_score == 0.92


def test_query_samples_p2_filters():
    mock_media = MagicMock()
    # Mock data needs P2 features in meta
    # Features can be nested in "features" dict as per audio_normalise impl
    results = [
        DerivedArtifact(
            id="a1", parent_asset_id="p1", tenant_id="t1", env="d", kind="audio_hit", uri="u1",
            meta={"features": {"key_root": "C", "brightness": 1200}}
        ),
        DerivedArtifact(
            id="a2", parent_asset_id="p2", tenant_id="t1", env="d", kind="audio_hit", uri="u2",
            meta={"features": {"key_root": "F#", "brightness": 500}}
        ),
        DerivedArtifact(
            id="a3", parent_asset_id="p3", tenant_id="t1", env="d", kind="audio_hit", uri="u3",
            meta={"features": {"key_root": "C", "brightness": 800}}
        )
    ]
    mock_media.list_artifacts.return_value = results
    
    svc = AudioSampleLibraryService(media_service=mock_media)
    
    # Filter by Key
    res = svc.query_samples(SampleLibraryQuery(
        tenant_id="t1", env="d",
        key_root="C"
    ))
    assert len(res.samples) == 2
    assert res.samples[0].key_root == "C"
    
    # Filter by Brightness (> 1000)
    res2 = svc.query_samples(SampleLibraryQuery(
        tenant_id="t1", env="d",
        min_brightness=1000
    ))
    assert len(res2.samples) == 1
    assert res2.samples[0].brightness == 1200


def test_query_samples_role_pagination():
    mock_media = MagicMock()
    results = [
        DerivedArtifact(
            id="r1", parent_asset_id="p1", tenant_id="t1", env="d", kind="audio_hit", uri="u1",
            meta={"role": "lead", "quality_score": 0.95}
        ),
        DerivedArtifact(
            id="r2", parent_asset_id="p2", tenant_id="t1", env="d", kind="audio_hit", uri="u2",
            meta={"role": "lead", "quality_score": 0.8}
        ),
        DerivedArtifact(
            id="r3", parent_asset_id="p3", tenant_id="t1", env="d", kind="audio_hit", uri="u3",
            meta={"role": "support", "quality_score": 0.9}
        )
    ]
    mock_media.list_artifacts.return_value = results
    svc = AudioSampleLibraryService(media_service=mock_media)

    q = SampleLibraryQuery(tenant_id="t1", env="d", role="lead", limit=1, offset=1)
    res = svc.query_samples(q)
    assert len(res.samples) == 1
    assert res.samples[0].role == "lead"
    assert res.total_count == 2


def test_query_samples_quality_upper_bound():
    mock_media = MagicMock()
    results = [
        DerivedArtifact(
            id="a1", parent_asset_id="p1", tenant_id="t1", env="d", kind="audio_hit", uri="u1",
            meta={"quality_score": 0.95}
        ),
        DerivedArtifact(
            id="a2", parent_asset_id="p2", tenant_id="t1", env="d", kind="audio_hit", uri="u2",
            meta={"quality_score": 0.8}
        )
    ]
    mock_media.list_artifacts.return_value = results
    svc = AudioSampleLibraryService(media_service=mock_media)

    q = SampleLibraryQuery(tenant_id="t1", env="d", max_quality_score=0.85)
    res = svc.query_samples(q)
    assert len(res.samples) == 1
    assert res.samples[0].artifact_id == "a2"
