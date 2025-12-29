
import tempfile
from pathlib import Path

# Fix: Import build_transition_plans for unit test
from engines.video_render.planner import build_transition_plans

from engines.media_v2.models import MediaUploadRequest
from engines.media_v2.service import InMemoryMediaRepository, LocalMediaStorage, MediaService, set_media_service
from engines.video_timeline.models import Clip, Filter, FilterStack, Sequence, Track, Transition, VideoProject
from engines.video_timeline.service import InMemoryTimelineRepository, TimelineService, set_timeline_service
from engines.video_render.service import set_render_service, RenderService
from engines.video_render.tests.helpers import make_video_render_client


def test_filters_and_transitions_in_plan():
    media_service = MediaService(repo=InMemoryMediaRepository(), storage=LocalMediaStorage())
    timeline_service = TimelineService(repo=InMemoryTimelineRepository())
    set_media_service(media_service)
    set_timeline_service(timeline_service)
    set_render_service(RenderService())

    vid = Path(tempfile.mkdtemp()) / "v.mp4"
    vid.write_bytes(b"video")
    asset = media_service.register_remote(MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="video", source_uri=str(vid)))

    project = timeline_service.create_project(VideoProject(tenant_id="t_test", env="dev", user_id="u1", title="Filters"))
    sequence = timeline_service.create_sequence(Sequence(tenant_id="t_test", env="dev", user_id="u1", project_id=project.id, name="Seq", timebase_fps=30))
    track = timeline_service.create_track(Track(tenant_id="t_test", env="dev", user_id="u1", sequence_id=sequence.id, kind="video", order=0))
    clip1 = timeline_service.create_clip(Clip(tenant_id="t_test", env="dev", user_id="u1", track_id=track.id, asset_id=asset.id, in_ms=0, out_ms=1000, start_ms_on_timeline=0))
    clip2 = timeline_service.create_clip(Clip(tenant_id="t_test", env="dev", user_id="u1", track_id=track.id, asset_id=asset.id, in_ms=0, out_ms=1000, start_ms_on_timeline=1000))
    # Filter stack on clip1 - using teeth_whiten as it is in KNOWN_FILTERS
    timeline_service.create_filter_stack(
        FilterStack(
            tenant_id="t_test",
            env="dev",
            user_id="u1",
            target_type="clip",
            target_id=clip1.id,
            filters=[Filter(type="teeth_whiten", params={"intensity": 0.5}, enabled=True)],
        )
    )
    # Transition between clips
    timeline_service.create_transition(
        Transition(
            tenant_id="t_test",
            env="dev",
            user_id="u1",
            sequence_id=sequence.id,
            type="crossfade",
            duration_ms=500,
            from_clip_id=clip1.id,
            to_clip_id=clip2.id,
        )
    )

    client = make_video_render_client()
    resp = client.post(
        "/video/render/dry-run",
        json={"tenant_id": "t_test", "env": "dev", "user_id": "u1", "project_id": project.id, "render_profile": "social_1080p_h264", "dry_run": True},
    )
    assert resp.status_code == 200
    plan = resp.json()["plan_preview"]
    # teeth_whiten maps to eq=brightness=...:contrast=...
    assert any("eq=" in f for f in plan["filters"])
    assert any("xfade" in f for f in plan["filters"])
    transitions = plan["meta"]["transitions"]
    assert transitions
    first = transitions[0]
    assert first["type"] == "crossfade"
    assert first["order"] == 0
    assert first["duration_ms"] > 0
    assert plan["meta"]["render_profile"] == "social_1080p_h264"
    assert plan["meta"]["render_profile_description"] == "1080p H.264 for social delivery with balanced quality"
    assert first["video_alias"] == "fade"
    assert first["audio_alias"] == "acrossfade"


def test_unknown_transition_rejection():
    """Verify that unknown transition types raise ValidationError (enforced by Pydantic model)."""
    from pydantic import ValidationError
    import pytest
    
    with pytest.raises(ValidationError) as excinfo:
        Transition(
            tenant_id="t_test",
            env="dev",
            sequence_id="s1",
            type="unknown_magic_swipe",
            duration_ms=500,
            from_clip_id="c1",
            to_clip_id="c2",
        )
    assert "Input should be 'crossfade'" in str(excinfo.value)


def test_transition_duration_clamping():
    """Verify that transition duration is clamped to clip lengths."""
    media_service = MediaService(repo=InMemoryMediaRepository(), storage=LocalMediaStorage())
    timeline_service = TimelineService(repo=InMemoryTimelineRepository())
    set_media_service(media_service)
    set_timeline_service(timeline_service)
    set_render_service(RenderService())
    
    # Asset setup
    vid = Path(tempfile.mkdtemp()) / "v.mp4"
    vid.write_bytes(b"video")
    asset = media_service.register_remote(MediaUploadRequest(tenant_id="t_test", env="dev", kind="video", source_uri=str(vid)))

    project = timeline_service.create_project(VideoProject(tenant_id="t_test", env="dev", title="Clamping"))
    sequence = timeline_service.create_sequence(Sequence(tenant_id="t_test", env="dev", project_id=project.id, name="Seq", timebase_fps=30))
    track = timeline_service.create_track(Track(tenant_id="t_test", env="dev", sequence_id=sequence.id, kind="video", order=0))
    
    # Clips are only 1000ms long
    clip1 = timeline_service.create_clip(Clip(tenant_id="t_test", env="dev", track_id=track.id, asset_id=asset.id, in_ms=0, out_ms=1000, start_ms_on_timeline=0))
    clip2 = timeline_service.create_clip(Clip(tenant_id="t_test", env="dev", track_id=track.id, asset_id=asset.id, in_ms=0, out_ms=1000, start_ms_on_timeline=1000))

    # Transition requested as 5000ms (too long)
    timeline_service.create_transition(
        Transition(
            tenant_id="t_test",
            env="dev",
            sequence_id=sequence.id,
            type="crossfade",
            duration_ms=5000,
            from_clip_id=clip1.id,
            to_clip_id=clip2.id,
        )
    )

    client = make_video_render_client()
    resp = client.post(
        "/video/render/dry-run",
        json={"tenant_id": "t_test", "env": "dev", "project_id": project.id, "render_profile": "social_1080p_h264"},
    )
    assert resp.status_code == 200
    plan = resp.json()["plan_preview"]
    t_meta = plan["meta"]["transitions"][0]
    
    # Logic in planner.py: duration_ms = min(duration_ms, clip_len)
    # Clip len is 1000. So it should be 1000.
    assert t_meta["duration_ms"] == 1000.0


def test_transition_presets_application_unit():
    """Verify that using a preset_id in meta sets the default duration and records it (using unit test to bypass strict timeline validation)."""
    
    # Setup mock clips
    clip1 = Clip(
        tenant_id="t_test", env="dev", track_id="track1", asset_id="asset1", 
        in_ms=0, out_ms=1000, start_ms_on_timeline=0
    )
    clip2 = Clip(
        tenant_id="t_test", env="dev", track_id="track1", asset_id="asset1", 
        in_ms=0, out_ms=1000, start_ms_on_timeline=1000
    )
    clips = {clip1.id: clip1, clip2.id: clip2}

    # Transition with preset_id "quick_crossfade" (should be 250ms)
    transition = Transition(
        tenant_id="t_test",
        env="dev",
        sequence_id="seq1",
        type="crossfade",
        duration_ms=0.0, # Will be overridden by preset logic in planner
        from_clip_id=clip1.id,
        to_clip_id=clip2.id,
        meta={"preset_id": "quick_crossfade"},
    )
    
    plans = build_transition_plans([transition], clips)
    assert len(plans) == 1
    t_meta = plans[0].to_meta()
    
    # quick_crossfade is 250ms
    assert t_meta["duration_ms"] == 250.0
    assert t_meta["preset_id"] == "quick_crossfade"
    assert t_meta["type"] == "crossfade"


def test_service_exposes_transition_catalog():
    service = RenderService()
    presets = service.get_transition_presets()
    assert "quick_crossfade" in presets
    assert presets["quick_crossfade"]["duration_ms"] == 250
    assert "dip_black" in presets
