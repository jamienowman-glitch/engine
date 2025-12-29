import pytest
from engines.audio_timeline.service import AudioTimelineService
from engines.audio_timeline.models import AutomationPoint

def test_timeline_structure():
    svc = AudioTimelineService()
    
    seq = svc.create_sequence("t1", "dev")
    assert seq.bpm == 120.0
    assert len(seq.tracks) == 0
    
    tr = svc.add_track(seq, "My Track")
    assert len(seq.tracks) == 1
    assert tr.name == "My Track"
    
    cl = svc.add_clip(tr, start_ms=1000, asset_id="a1")
    assert cl.start_ms == 1000
    assert cl.asset_id == "a1"
    assert len(tr.clips) == 1

def test_add_clip_validation():
    svc = AudioTimelineService()
    seq = svc.create_sequence("t1", "dev")
    tr = svc.add_track(seq)
    
    with pytest.raises(ValueError):
        svc.add_clip(tr, start_ms=0) # Missing asset/artifact id

def test_clip_automation_and_role():
    svc = AudioTimelineService()
    seq = svc.create_sequence("t1", "dev")
    tr = svc.add_track(seq, role="drums")
    clip = svc.add_clip(tr, start_ms=0, duration_ms=1000, asset_id="a1")
    
    points = [
        AutomationPoint(time_ms=100, value=-3.0),
        AutomationPoint(time_ms=1000, value=0.0)
    ]
    svc.add_clip_automation(clip, "gain", points)
    
    assert "gain" in clip.automation
    assert clip.automation["gain"][0].value == -3.0
    assert tr.meta["role"] == "drums"

def test_clip_fade_limits():
    svc = AudioTimelineService()
    seq = svc.create_sequence("t1", "dev")
    tr = svc.add_track(seq)
    
    with pytest.raises(ValueError):
        svc.add_clip(tr, start_ms=0, duration_ms=500, asset_id="a1", fade_in_ms=300, fade_out_ms=250)

def test_clip_crossfade_limits():
    svc = AudioTimelineService()
    seq = svc.create_sequence("t1", "dev")
    tr = svc.add_track(seq)

    with pytest.raises(ValueError):
        svc.add_clip(tr, start_ms=0, duration_ms=500, asset_id="a1", crossfade_in_ms=300, crossfade_out_ms=250)

def test_track_automation_validation():
    svc = AudioTimelineService()
    seq = svc.create_sequence("t1", "dev")
    tr = svc.add_track(seq)

    points = [
        AutomationPoint(time_ms=100, value=1.0),
        AutomationPoint(time_ms=200, value=0.5)
    ]
    svc.add_track_automation(tr, "gain", points)
    assert "gain" in tr.automation
    assert tr.automation["gain"][0].value == 1.0

    with pytest.raises(ValueError):
        svc.add_track_automation(tr, "gain", [
            AutomationPoint(time_ms=50, value=0.0),
            AutomationPoint(time_ms=50, value=0.0),
        ])


def test_clip_automation_out_of_bounds():
    svc = AudioTimelineService()
    seq = svc.create_sequence("t1", "dev")
    tr = svc.add_track(seq)
    clip = svc.add_clip(tr, start_ms=0, duration_ms=1000, asset_id="a1")
    with pytest.raises(ValueError):
        svc.add_clip_automation(clip, "gain", [
            AutomationPoint(time_ms=1100, value=0.0)
        ])
