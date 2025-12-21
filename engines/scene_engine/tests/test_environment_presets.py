"""Tests for Environment Presets (P8)."""

from engines.scene_engine.environment.presets import apply_environment_preset, CYBERPUNK_NEON
from engines.scene_engine.core.scene_v2 import SceneV2
from engines.scene_engine.camera.models import LightKind

def test_apply_neon_preset():
    scene = SceneV2(id="s1")
    scene = apply_environment_preset(scene, "cyberpunk_neon")
    
    assert len(scene.lights) == 3
    # Check for Pink light
    pink_light = next((l for l in scene.lights if l.color.x > 0.8 and l.color.y < 0.2), None)
    assert pink_light is not None
    assert pink_light.kind == LightKind.POINT
    
    assert scene.environment["ambient_color"]["z"] > 0.05 # Blueish ambient
