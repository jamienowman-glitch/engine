import pytest
from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.video_presets.models import FilterPreset, MotionPreset
from engines.video_presets.service import InMemoryPresetRepository, PresetService, set_preset_service


def setup_module(_module):
    set_preset_service(PresetService(repo=InMemoryPresetRepository()))


def test_filter_preset_crud():
    set_preset_service(PresetService(repo=InMemoryPresetRepository()))
    client = TestClient(create_app())
    preset = FilterPreset(tenant_id="t_test", env="dev", user_id="u1", name="pop", filters=[], tags=["pop"])
    resp = client.post("/video/presets/filters", json=preset.model_dump())
    assert resp.status_code == 200
    preset_id = resp.json()["id"]

    resp_get = client.get(f"/video/presets/filters/{preset_id}")
    assert resp_get.status_code == 200
    resp_list = client.get("/video/presets/filters", params={"tenant_id": "t_test", "env": "dev"})
    assert resp_list.status_code == 200
    assert any(p["id"] == preset_id for p in resp_list.json())

    resp_del = client.delete(f"/video/presets/filters/{preset_id}")
    assert resp_del.status_code == 200


def test_motion_presets_include_built_ins():
    set_preset_service(PresetService(repo=InMemoryPresetRepository()))
    client = TestClient(create_app())
    resp_list = client.get("/video/presets/motion", params={"tenant_id": "t_test", "env": "dev"})
    assert resp_list.status_code == 200
    presets = resp_list.json()
    assert any("shake_1" == p["name"] for p in presets)
    # create a custom preset
    mp = MotionPreset(
        tenant_id="t_test",
        env="dev",
        user_id="u1",
        name="shake_custom",
        description=None,
        duration_ms=500,
        tracks=[],
    )
    resp = client.post("/video/presets/motion", json=mp.model_dump())
    assert resp.status_code == 200
    resp_list2 = client.get("/video/presets/motion", params={"tenant_id": "t_test", "env": "dev"})
    assert any(p["name"] == "shake_custom" for p in resp_list2.json())
    assert any(p["name"].startswith("steady_pan") for p in resp_list2.json())


def test_style_presets_cinematc_metadata():
    client = TestClient(create_app())
    resp = client.get("/video/presets/filters", params={"tenant_id": "t_test", "env": "dev"})
    assert resp.status_code == 200
    presets = resp.json()
    style_names = ["style_cinematic", "style_vlog", "style_punchy", "style_monochrome"]
    for name in style_names:
        entry = next((p for p in presets if p["name"] == name), None)
        assert entry is not None, f"{name} should exist"
        assert entry["meta"].get("render_profiles")

    profile_defaults = {
        "profile_default_social_1080p_h264": "social_1080p_h264",
        "profile_default_preview_720p_fast": "preview_720p_fast",
        "profile_default_draft_480p_fast": "draft_480p_fast",
    }
    for preset_name, profile in profile_defaults.items():
        entry = next((p for p in presets if p["name"] == preset_name), None)
        assert entry is not None, f"{preset_name} should exist"
        assert entry["meta"].get("render_profiles") == [profile]
