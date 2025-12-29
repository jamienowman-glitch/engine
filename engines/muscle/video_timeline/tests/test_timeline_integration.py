
import pytest
from engines.video_timeline.service import TimelineService, InMemoryTimelineRepository, set_timeline_service
from engines.video_timeline.models import VideoProject, Sequence, Track, Clip

@pytest.fixture
def service():
    s = TimelineService(repo=InMemoryTimelineRepository())
    return s

def test_trim_ripple(service):
    # Setup
    p = service.create_project(VideoProject(tenant_id="t1", env="dev", title="P"))
    s = service.create_sequence(Sequence(tenant_id="t1", env="dev", project_id=p.id, name="S"))
    t = service.create_track(Track(tenant_id="t1", env="dev", sequence_id=s.id, kind="video"))
    
    # C1: 0-1000
    c1 = service.create_clip(Clip(
        tenant_id="t1", env="dev", track_id=t.id, asset_id="a1", 
        in_ms=0, out_ms=1000, start_ms_on_timeline=0
    ))
    # C2: 1000-2000
    c2 = service.create_clip(Clip(
        tenant_id="t1", env="dev", track_id=t.id, asset_id="a2",
        in_ms=0, out_ms=1000, start_ms_on_timeline=1000
    ))
    
    # Trim C1 to 500ms (delta = -500), ripple=True
    service.trim_clip(c1.id, new_in_ms=0, new_out_ms=500, ripple=True)
    
    # Verify C2 shifted left by 500
    c2_upd = service.get_clip(c2.id)
    assert c2_upd.start_ms_on_timeline == 500

def test_split_clip(service):
    p = service.create_project(VideoProject(tenant_id="t1", env="dev", title="P"))
    s = service.create_sequence(Sequence(tenant_id="t1", env="dev", project_id=p.id, name="S"))
    t = service.create_track(Track(tenant_id="t1", env="dev", sequence_id=s.id, kind="video"))
    
    # C1: 0-2000 (Timeline) -> Asset 0-2000
    c1 = service.create_clip(Clip(
        tenant_id="t1", env="dev", track_id=t.id, asset_id="a1",
        in_ms=0, out_ms=2000, start_ms_on_timeline=0
    ))
    
    # Split at 1000
    c2 = service.split_clip(c1.id, split_time_on_timeline_ms=1000)
    
    c1_upd = service.get_clip(c1.id)
    
    # C1: 0-1000 on timeline
    assert c1_upd.out_ms == 1000
    assert c1_upd.start_ms_on_timeline == 0
    
    # C2: 1000-2000 on timeline, Asset 1000-2000
    assert c2.start_ms_on_timeline == 1000
    assert c2.in_ms == 1000
    assert c2.out_ms == 2000

def test_move_clip_ripple(service):
    p = service.create_project(VideoProject(tenant_id="t1", env="dev", title="P"))
    s = service.create_sequence(Sequence(tenant_id="t1", env="dev", project_id=p.id, name="S"))
    t = service.create_track(Track(tenant_id="t1", env="dev", sequence_id=s.id, kind="video"))
    
    # C1: 0-1000
    c1 = service.create_clip(Clip(
        tenant_id="t1", env="dev", track_id=t.id, asset_id="a1", 
        in_ms=0, out_ms=1000, start_ms_on_timeline=0
    ))
    # C2: 1000-2000
    c2 = service.create_clip(Clip(
        tenant_id="t1", env="dev", track_id=t.id, asset_id="a2",
        in_ms=0, out_ms=1000, start_ms_on_timeline=1000
    ))
    # C3 (New): 500ms long
    c3 = service.create_clip(Clip(
        tenant_id="t1", env="dev", track_id=t.id, asset_id="a3",
        in_ms=0, out_ms=500, start_ms_on_timeline=5000 # far out initially
    ))
    
    # Move C3 to 0, ripple=True -> should push C1, C2 right by 500
    service.move_clip(c3.id, new_start_ms=0, ripple=True)
    
    c1_upd = service.get_clip(c1.id)
    c2_upd = service.get_clip(c2.id)
    
    
    assert c1_upd.start_ms_on_timeline == 500
    assert c2_upd.start_ms_on_timeline == 1500

def test_create_filter_stack_validation(service):
    # Valid
    p = service.create_project(VideoProject(tenant_id="t1", env="dev", title="P"))
    
    # Invalid Filter
    from engines.video_timeline.models import FilterStack, Filter
    stack = FilterStack(
        tenant_id="t1", env="dev", target_type="clip", target_id="c1",
        filters=[Filter(type="invalid_filter")]
    )
    with pytest.raises(ValueError, match="Unknown filter type"):
        service.create_filter_stack(stack)

    # Valid Filter
    stack_ok = FilterStack(
        tenant_id="t1", env="dev", target_type="clip", target_id="c1",
        filters=[Filter(type="color_grade", params={"saturation": 1.2})]
    )
    assert service.create_filter_stack(stack_ok) is not None

def test_create_transition_validation(service):
    from engines.video_timeline.models import Transition
    # Invalid duration
    tr = Transition(
        tenant_id="t1", env="dev", sequence_id="s1", type="crossfade",
        duration_ms=0, from_clip_id="c1", to_clip_id="c2"
    )

    with pytest.raises(ValueError, match="duration"):
        service.create_transition(tr)

def test_promote_multicam(service):
    # Setup
    p = service.create_project(VideoProject(tenant_id="t1", env="dev", title="P"))
    
    multicam_payload = {
        "tenant_id": "t1", "env": "dev",
        "cuts": [
            {"asset_id": "a1", "start_ms": 100, "end_ms": 1100, "meta": {"score": 0.9}},
            {"asset_id": "a2", "start_ms": 200, "end_ms": 700, "meta": {"score": 0.8}}
        ],
        "meta": {"alignment_version": "v1"}
    }
    
    seq = service.promote_multicam_to_sequence(p.id, "MC Seq", multicam_payload)
    
    assert seq is not None
    tracks = service.list_tracks_for_sequence(seq.id)
    assert len(tracks) == 1
    t = tracks[0]
    assert t.video_role == "main"
    
    clips = service.list_clips_for_track(t.id)
    assert len(clips) == 2
    
    # Clip 1
    c1 = clips[0]
    assert c1.asset_id == "a1"
    assert c1.in_ms == 100
    assert c1.out_ms == 1100
    assert c1.start_ms_on_timeline == 0
    assert c1.alignment_applied == True
    assert c1.meta["score"] == 0.9
    
    # Clip 2
    c2 = clips[1]
    assert c2.asset_id == "a2"
    assert c2.in_ms == 200
    assert c2.out_ms == 700
    assert c2.start_ms_on_timeline == 1000 # 0 + (1100-100)

def test_ingest_assist(service):
    p = service.create_project(VideoProject(tenant_id="t1", env="dev", title="P"))
    s = service.create_sequence(Sequence(tenant_id="t1", env="dev", project_id=p.id, name="S"))
    
    assist_payload = {
        "tenant_id": "t1", "env": "dev",
        "segments": [
            {"asset_id": "a1", "in_ms": 1000, "out_ms": 5000, "meta": {"energy": 0.95}}
        ]
    }
    
    track = service.ingest_assist_highlights(s.id, assist_payload)
    assert track.video_role == "b-roll"
    
    clips = service.list_clips_for_track(track.id)
    assert len(clips) == 1
    c = clips[0]
    assert c.in_ms == 1000
    assert c.out_ms == 5000
    assert c.meta["energy"] == 0.95

def test_apply_focus(service):
    # Create clip first
    p = service.create_project(VideoProject(tenant_id="t1", env="dev", title="P"))
    s = service.create_sequence(Sequence(tenant_id="t1", env="dev", project_id=p.id, name="S"))
    t = service.create_track(Track(tenant_id="t1", env="dev", sequence_id=s.id, kind="video"))
    c = service.create_clip(Clip(tenant_id="t1", env="dev", track_id=t.id, asset_id="a1", in_ms=0, out_ms=5000, start_ms_on_timeline=0))
    
    focus_payload = {
        "tenant_id": "t1", "env": "dev",
        "keyframes": [
            {"time_ms": 0, "crop_x": 0.5, "crop_y": 0.5},
            {"time_ms": 1000, "crop_x": 0.6, "crop_y": 0.4}
        ]
    }
    
    autos = service.apply_focus_automation(c.id, focus_payload)
    assert len(autos) == 2 # one for crop_x, one for crop_y
    
    # Check crop_x
    ax = next(a for a in autos if a.property == "crop_x")
    assert len(ax.keyframes) == 2
    assert ax.keyframes[1].value == 0.6
    
    # Check crop_y
    ay = next(a for a in autos if a.property == "crop_y")
    assert len(ay.keyframes) == 2
    assert ay.keyframes[1].value == 0.4

def test_persistence_roundtrip(service):
    # Create complete timeline structure
    p = service.create_project(VideoProject(tenant_id="t1", env="dev", title="Roundtrip"))
    s = service.create_sequence(Sequence(tenant_id="t1", env="dev", project_id=p.id, name="S"))
    
    # Create Track 1 (Order 1)
    t1 = service.create_track(Track(tenant_id="t1", env="dev", sequence_id=s.id, kind="video", order=1))
    # Create Track 2 (Order 0) - should come first in list
    t2 = service.create_track(Track(tenant_id="t1", env="dev", sequence_id=s.id, kind="audio", order=0))
    
    # Create Clips on T1
    c1 = service.create_clip(Clip(tenant_id="t1", env="dev", track_id=t1.id, asset_id="a1", in_ms=0, out_ms=1000, start_ms_on_timeline=1000))
    c2 = service.create_clip(Clip(tenant_id="t1", env="dev", track_id=t1.id, asset_id="a2", in_ms=0, out_ms=1000, start_ms_on_timeline=0))
    
    # Reload Sequence
    s_loaded = service.get_sequence(s.id)
    assert s_loaded.id == s.id
    
    # Check Track Order (should be sorted by 'order')
    tracks = service.list_tracks_for_sequence(s.id)
    assert len(tracks) == 2
    assert tracks[0].id == t2.id # order 0
    assert tracks[1].id == t1.id # order 1
    
    # Check Clip Order (should be sorted by 'start_ms_on_timeline')
    clips = service.list_clips_for_track(t1.id)
    assert len(clips) == 2
    assert clips[0].id == c2.id # start 0
    assert clips[1].id == c1.id # start 1000
    
    # Check Metadata persistence
    assert s_loaded.tenant_id == "t1"
    
    # Automation persistence
    from engines.video_timeline.models import ParameterAutomation, Keyframe
    service.create_automation(ParameterAutomation(
        tenant_id="t1", env="dev", target_type="clip", target_id=c1.id, 
        property="opacity", keyframes=[Keyframe(time_ms=0, value=1.0)]
    ))
    
    autos = service.list_automation("clip", c1.id)
    assert len(autos) == 1
    assert autos[0].property == "opacity"
