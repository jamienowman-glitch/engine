import pytest
from unittest.mock import MagicMock
from engines.audio_structure_engine.service import AudioStructureEngineService, ArrangementRequest
from engines.audio_structure_engine.models import StructureTemplate, StructureSection
from engines.audio_structure_engine.templates import STRUCTURE_TEMPLATES

def test_arrange_song_simple():
    # Use a simpler custom template or mock the template dict?
    # We can inject into STRUCTURE_TEMPLATES or test the logic with the real "pop_structure_1"
    
    svc = AudioStructureEngineService()
    
    # Mock clip patterns
    # Role "kick": 1 clip at 0ms.
    kick_pattern = [{"start_ms": 0.0, "asset_id": "kick1", "duration_ms": 500.0}]
    
    req = ArrangementRequest(
        tenant_id="t1", env="d", template_id="pop_structure_1",
        pattern_clips_by_role={"kick": kick_pattern},
        bpm=120.0 # 1 bar = 2000ms
    )
    
    res = svc.arrange_song(req)
    
    seq = res.sequence
    
    # Expected duration:
    # Pop structure: Intro 4 + V1 8 + C1 8 + V2 8 + C2 16 + Outro 4 = 48 bars.
    # 48 * 2000ms = 96,000ms.
    assert seq.duration_ms == 96000.0
    
    # Check Kick track
    # Kick is active in Verse 1, Chorus 1, Verse 2, Chorus 2.
    # Intro/Outro have no kick in standard pop template defined?
    # Template: Intro=["hat", "fx"], Verse1=["kick", ...], Chorus1=["kick"...]
    
    # Find kick track
    kick_tracks = [t for t in seq.tracks if "Kick" in t.name]
    assert len(kick_tracks) == 1
    t = kick_tracks[0]
    
    # Count clips
    # Bars with kick: 8 (V1) + 8 (C1) + 8 (V2) + 16 (C2) = 40 bars.
    # 1 clip per bar -> 40 clips.
    assert len(t.clips) == 40
    
    # Check first clip
    # V1 starts after Intro (4 bars = 8000ms).
    # So first kick should be at 8000.0
    times = sorted([c.start_ms for c in t.clips])
    assert times[0] == 8000.0
