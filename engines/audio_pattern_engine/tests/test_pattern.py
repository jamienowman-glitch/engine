import pytest
from engines.audio_pattern_engine.service import AudioPatternEngineService
from engines.audio_pattern_engine.models import PatternRequest

# BPM 120: 1 beat = 500ms. 16th = 125ms.
# 4/4 Bar = 2000ms.

def test_four_on_floor_timing():
    svc = AudioPatternEngineService()
    req = PatternRequest(
        tenant_id="t1", env="d",
        template_id="four_on_the_floor",
        sample_map={"kick": "k1", "snare": "s1", "hat": "h1"},
        bpm=120.0,
        swing_pct=0.0
    )
    
    res = svc.generate_pattern(req)
    clips = res.clips
    
    # Check Kicks (Role "kick")
    kicks = [c for c in clips if c["artifact_id"] == "k1"]
    # Check start times. Indices 0, 4, 8, 12 should be 0, 500, 1000, 1500 ms
    times = sorted([c["start_ms"] for c in kicks])
    assert len(times) == 4
    assert times[0] == 0.0
    assert times[1] == 500.0
    assert times[2] == 1000.0
    assert times[3] == 1500.0

def test_boom_bap_swing():
    svc = AudioPatternEngineService()
    req = PatternRequest(
        tenant_id="t1", env="d",
        template_id="boom_bap_90",
        sample_map={"kick": "k1", "hat": "h1"},
        bpm=120.0, # Use 120 for easier math (16th = 125ms)
        swing_pct=20.0 
    )
    
    # 20% swing offset = 0.2 * (125 * 0.5) = 12.5ms roughly?
    # Logic: swing_offset_ms = (swing_pct / 100.0) * (ms_per_16th * 0.5)
    # 0.2 * 62.5 = 12.5ms.
    
    res = svc.generate_pattern(req)
    
    # Find a hat on an odd step.
    # boom_bap_90 hat is fill (all steps).
    hats = sorted([c for c in res.clips if c["artifact_id"] == "h1"], key=lambda k: k["start_ms"])
    
    # Step 0 (0ms) -> No swing
    assert hats[0]["start_ms"] == 0.0
    
    # Step 1 (125ms base) -> + swing
    expected_1 = 125.0 + ((20/100) * (125*0.5)) 
    # 125 + 12.5 = 137.5
    assert abs(hats[1]["start_ms"] - expected_1) < 0.1

def test_missing_sample_role():
    svc = AudioPatternEngineService()
    req = PatternRequest(
        tenant_id="t1", env="d",
        template_id="four_on_the_floor",
        sample_map={"kick": "k1"} # No snare, no hat
    )
    
    res = svc.generate_pattern(req)
    # Should only have kicks
    for c in res.clips:
        assert c["artifact_id"] == "k1"
    
    # Ensure no crashes
    assert len(res.clips) > 0
