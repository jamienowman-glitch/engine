from unittest.mock import MagicMock

from engines.audio_field_to_samples.service import AudioFieldToSamplesService
from engines.audio_field_to_samples.models import FieldToSamplesRequest
from engines.audio_hits.models import HitDetectResult, HitEvent
from engines.audio_loops.models import LoopDetectResult, LoopEvent
from engines.audio_voice_phrases.models import VoicePhraseDetectResult, VoicePhrase

def test_process_asset_pipeline():
    # Mock Sub-Services
    mock_hits = MagicMock()
    mock_hits.detect_hits.return_value = HitDetectResult(
        events=[
            HitEvent(time_ms=100.0, peak_db=-5.0, source_start_ms=100.0, source_end_ms=200.0, energy=0.8),
            HitEvent(time_ms=300.0, peak_db=-25.0, source_start_ms=300.0, source_end_ms=400.0, energy=0.2),
        ],
        artifact_ids=["h1", "h2"],
        meta={
            "scores": {"h1": 0.85, "h2": 0.35},
            "backend_info": {"backend_version": "librosa-0.10"}
        }
    )
    
    mock_loops = MagicMock()
    mock_loops.detect_loops.return_value = LoopDetectResult(
        loops=[LoopEvent(start_ms=0.0, end_ms=4000.0, loop_bars=2, bpm=120.0, confidence=0.9, source_start_ms=0.0, source_end_ms=4000.0)],
        artifact_ids=["l1"],
        meta={
            "scores": {"l1": 0.92},
            "backend_info": {"backend_version": "librosa-0.10"}
        }
    )
    
    mock_phrases = MagicMock()
    mock_phrases.detect_phrases.return_value = VoicePhraseDetectResult(
        phrases=[VoicePhrase(start_ms=0.0, end_ms=1000.0, transcript="Yo", confidence=0.8, source_start_ms=0.0, source_end_ms=1000.0)],
        artifact_ids=["p1"],
        meta={
            "scores": {"p1": 0.7},
            "backend_info": {"backend_version": "librosa-0.10"}
        }
    )
    
    service = AudioFieldToSamplesService(
        hits_service=mock_hits,
        loops_service=mock_loops,
        phrases_service=mock_phrases
    )
    
    req = FieldToSamplesRequest(
        tenant_id="t1", env="dev", asset_id="a1",
        hit_params={"min_peak_db": -20},
        min_quality_score=0.5
    )
   
    res = service.process_asset(req)
    
    # Check Aggregation
    assert res.hit_artifact_ids == ["h1"]
    assert len(res.loop_artifact_ids) == 1
    assert len(res.phrase_artifact_ids) == 1
    assert res.summary_meta["hits_count"] == 1
    assert res.summary_meta["score_details"]["hits"]["h1"]["score"] >= 0.8
    assert res.summary_meta["score_details"]["hits"]["h1"]["offset_ms"] == 100.0
    assert "h2" not in res.summary_meta["score_details"]["hits"]
    cache_key = res.summary_meta["cache_key"]
    assert len(cache_key) == 64
    backend_versions = res.summary_meta["backend_versions"]
    assert backend_versions["hits"] == "librosa-0.10"
    assert backend_versions["loops"] == "librosa-0.10"
    assert backend_versions["phrases"] == "librosa-0.10"

    # Check Call Params
    args, _ = mock_hits.detect_hits.call_args
    hit_req = args[0]
    assert hit_req.asset_id == "a1"
    assert hit_req.min_peak_db == -20

def test_process_asset_partial_fail():
    # Test that phrase failure doesn't crash pipe
    mock_hits = MagicMock()
    mock_hits.detect_hits.return_value = HitDetectResult()
    mock_loops = MagicMock()
    mock_loops.detect_loops.return_value = LoopDetectResult()
    
    mock_phrases = MagicMock()
    mock_phrases.detect_phrases.side_effect = Exception("No transcript")
    
    service = AudioFieldToSamplesService(
        hits_service=mock_hits,
        loops_service=mock_loops,
        phrases_service=mock_phrases
    )
    
    req = FieldToSamplesRequest(tenant_id="t", env="d", asset_id="a")
    res = service.process_asset(req)
    
    # Should succeed with 0 phrases
    assert len(res.phrase_artifact_ids) == 0
    assert res.summary_meta["phrases_count"] == 0
    assert "phrases" in res.summary_meta["errors"]


def test_cache_key_determinism():
    def build_service():
        mock_hits = MagicMock()
        mock_hits.detect_hits.return_value = HitDetectResult(
            events=[HitEvent(time_ms=0, peak_db=-6.0, source_start_ms=0.0, source_end_ms=100.0, energy=0.7)],
            artifact_ids=["h_d"],
            meta={"scores": {"h_d": 0.9}, "backend_info": {"backend_version": "librosa-0.10"}}
        )
        mock_loops = MagicMock()
        mock_loops.detect_loops.return_value = LoopDetectResult(
            loops=[],
            artifact_ids=[],
            meta={"backend_info": {"backend_version": "librosa-0.10"}}
        )
        mock_phrases = MagicMock()
        mock_phrases.detect_phrases.return_value = VoicePhraseDetectResult(
            phrases=[],
            artifact_ids=[],
            meta={"backend_info": {"backend_version": "librosa-0.10"}}
        )
        return AudioFieldToSamplesService(
            hits_service=mock_hits,
            loops_service=mock_loops,
            phrases_service=mock_phrases
        )

    req = FieldToSamplesRequest(tenant_id="t", env="d", asset_id="a1")
    res1 = build_service().process_asset(req)
    res2 = build_service().process_asset(req)
    assert res1.summary_meta["cache_key"] == res2.summary_meta["cache_key"]


def test_min_quality_score_bounds():
    mock_hits = MagicMock()
    mock_hits.detect_hits.return_value = HitDetectResult(meta={"backend_info": {"backend_version": "librosa-0.10"}})
    mock_loops = MagicMock()
    mock_loops.detect_loops.return_value = LoopDetectResult(meta={"backend_info": {"backend_version": "librosa-0.10"}})
    mock_phrases = MagicMock()
    mock_phrases.detect_phrases.return_value = VoicePhraseDetectResult(meta={"backend_info": {"backend_version": "librosa-0.10"}})

    service = AudioFieldToSamplesService(
        hits_service=mock_hits,
        loops_service=mock_loops,
        phrases_service=mock_phrases
    )

    req = FieldToSamplesRequest(tenant_id="t", env="d", asset_id="a", min_quality_score=-2.0)
    res = service.process_asset(req)
    assert res.summary_meta["min_quality_score"] == 0.0
