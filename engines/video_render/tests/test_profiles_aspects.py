
import pytest
from engines.video_render.profiles import PROFILE_MAP, PROFILE_GPU_PREFERENCES

def test_social_4_3_profile_exists():
    assert "social_4_3_h264" in PROFILE_MAP
    prof = PROFILE_MAP["social_4_3_h264"]
    assert prof["width"] == 1440
    assert prof["height"] == 1080
    assert abs(prof["width"] / prof["height"] - 1.333) < 0.01
    assert "social_4_3_h264" in PROFILE_GPU_PREFERENCES

def test_social_1_1_profile_exists():
    assert "social_1_1_h264" in PROFILE_MAP
    prof = PROFILE_MAP["social_1_1_h264"]
    assert prof["width"] == 1080
    assert prof["height"] == 1080
    assert prof["width"] == prof["height"]
    assert "social_1_1_h264" in PROFILE_GPU_PREFERENCES

def test_render_profiles_have_descriptions():
    for name, prof in PROFILE_MAP.items():
        if "description" in prof:
             assert isinstance(prof["description"], str)
             assert len(prof["description"]) > 5

def test_gpu_preferences_coverage():
    """Ensure all profiles have an entry in GPU preferences (even if empty list)."""
    for profile in PROFILE_MAP:
        assert profile in PROFILE_GPU_PREFERENCES
