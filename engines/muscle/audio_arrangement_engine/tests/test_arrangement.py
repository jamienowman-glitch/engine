import pytest
from engines.audio_arrangement_engine.service import AudioArrangementEngineService, ArrangementRequest
from engines.audio_timeline.service import AudioTimelineService
from engines.audio_arrangement_engine.templates import STRUCTURE_TEMPLATES

def test_arrange_simple_pop():
    # Mock Timeline Service (using real logic but in-memory models)
    # Since Arrangement service uses get_audio_timeline_service which uses global, 
    # we can trust it instantiates fresh default service if none set, or use real one.
    # The real one doesn't depend on external IO for model creation, so it's safe.
    
    svc = AudioArrangementEngineService()
    
    # define patterns
    # Role: "drums". Pattern: 1 kick at 0ms.
    clip = {"start_ms": 0.0, "asset_id": "kick", "duration_ms": 500}
    patterns = {
        "drums": [clip],
        "bass": [{"start_ms": 0.0, "asset_id": "bass", "duration_ms": 500}],
        "keys": [{"start_ms": 0.0, "asset_id": "keys", "duration_ms": 500}]
    }
    
    req = ArrangementRequest(
        tenant_id="t", env="d", template_id="pop_standard",
        bpm=120.0,
        pattern_clips_by_role=patterns
    )
    
    res = svc.generate_arrangement(req)
    
    seq = res.sequence
    
    # Verify Markers
    # pop_standard: Intro(4), Verse 1(8), Chorus 1(8)...
    # Intro starts at 0.
    assert seq.markers[0].name == "Intro"
    assert seq.markers[0].start_ms == 0.0
    
    # Verse 1 starts at 4 bars * 2000ms (120bpm -> 500ms beat -> 2s bar) = 8000ms
    assert seq.markers[1].name == "Verse 1"
    assert seq.markers[1].start_ms == 8000.0
    
    # Verify Clip Placement
    # Intro: Drums, Keys. (Bass inactive).
    # Check Bass track in 0-8000ms window -> Should be empty.
    
    t_bass = next(t for t in seq.tracks if t.meta["role"] == "bass")
    clips_in_intro = [c for c in t_bass.clips if c.start_ms < 8000]
    assert len(clips_in_intro) == 0
    
    # Verse 1: Bass active. Should have clips.
    # Verse 1 length 8 bars. 1 clip per bar -> 8 clips.
    clips_in_verse = [c for c in t_bass.clips if c.start_ms >= 8000 and c.start_ms < (8000 + 8*2000)]
    assert len(clips_in_verse) == 8
    
    # Check total duration
    # Intro(4) + V1(8) + C1(8) + V2(8) + C2(8) + Outro(4) = 40 bars.
    # 40 * 2s = 80s = 80000ms.
    assert seq.duration_ms == 80000.0
