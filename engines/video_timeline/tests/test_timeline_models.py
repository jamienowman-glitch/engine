
import pytest
from pydantic import ValidationError
from engines.video_timeline.models import (
    VideoProject, Sequence, Track, Clip, Transition, 
    FilterStack, Filter, ParameterAutomation, Keyframe
)

def test_track_roles():
    # Test valid video roles
    t = Track(
        tenant_id="t1", env="dev", sequence_id="s1", kind="video", 
        video_role="main"
    )
    assert t.video_role == "main"
    
    # Test valid audio roles
    t_audio = Track(
        tenant_id="t1", env="dev", sequence_id="s1", kind="audio", 
        audio_role="music"
    )
    assert t_audio.audio_role == "music"

    # Test invalid roles (should fail if strict Pydantic validation is on? 
    # Literal enforces it at init time usually)
    with pytest.raises(ValidationError):
        Track(
            tenant_id="t1", env="dev", sequence_id="s1", kind="video",
            video_role="invalid_role"
        )

def test_clip_alignment_field():
    c = Clip(
        tenant_id="t1", env="dev", track_id="tr1", asset_id="a1",
        in_ms=0, out_ms=1000, start_ms_on_timeline=0,
        alignment_applied=True
    )
    assert c.alignment_applied is True
    
    c_default = Clip(
        tenant_id="t1", env="dev", track_id="tr1", asset_id="a1",
        in_ms=0, out_ms=1000, start_ms_on_timeline=0
    )
    assert c_default.alignment_applied is False

def test_clip_bounds_validation():
    # Pydantic V2 or custom validators would be needed for logic like out_ms > in_ms
    # Currently pure schema, but checking types at least.
    with pytest.raises(ValidationError):
        Clip(
            tenant_id="t1", env="dev", track_id="tr1", asset_id="a1",
            in_ms="not_a_number", out_ms=1000, start_ms_on_timeline=0
        )

def test_transition_types():
    # Valid
    tr = Transition(
        tenant_id="t1", env="dev", sequence_id="s1",
        type="crossfade", duration_ms=500,
        from_clip_id="c1", to_clip_id="c2"
    )
    assert tr.type == "crossfade"
    
    # Invalid
    with pytest.raises(ValidationError):
        Transition(
            tenant_id="t1", env="dev", sequence_id="s1",
            type="star_wipe", duration_ms=500,
            from_clip_id="c1", to_clip_id="c2"
        )

def test_deterministic_ids():
    # Basic check that IDs are generated if missing
    p = VideoProject(tenant_id="t1", env="dev", title="Test")
    assert len(p.id) > 0
    assert isinstance(p.id, str)

def test_metadata_persistence():
    meta = {"alignment_offset_ms": 100, "scoring_version": "v1"}
    c = Clip(
        tenant_id="t1", env="dev", track_id="tr1", asset_id="a1",
        in_ms=0, out_ms=1000, start_ms_on_timeline=0,
        meta=meta
    )
    assert c.meta["alignment_offset_ms"] == 100
