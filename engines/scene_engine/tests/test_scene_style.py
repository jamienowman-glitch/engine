"""Tests for Scene Style & Theme Engine (P14)."""

from engines.scene_engine.style.theme import SceneTheme, ColorPalette, apply_theme
from engines.scene_engine.core.scene_v2 import SceneV2
from engines.scene_engine.core.geometry import Material, Vector3
import uuid

def test_apply_theme_palette():
    scene = SceneV2(id=str(uuid.uuid4()))
    
    # Material with name matching palette
    m1 = Material(id="m1", name="primary", meta={})
    # Material with style_class matching palette
    m2 = Material(id="m2", name="random_name", meta={"style_class": "secondary"})
    # Material with no match
    m3 = Material(id="m3", name="nomatch", meta={})
    
    scene.materials = [m1, m2, m3]
    
    # Custom Palette
    theme = SceneTheme(
        name="TestTheme",
        palette=ColorPalette(
            primary=Vector3(x=0, y=0, z=1), # Blue
            secondary=Vector3(x=1, y=0, z=0) # Red
        )
    )
    
    apply_theme(scene, theme)
    
    # m1 should be Blue (primary)
    assert m1.base_color.z == 1.0
    
    # m2 should be Red (secondary)
    assert m2.base_color.x == 1.0
    
    # m3 (no match) should be None (default)
    assert m3.base_color is None

def test_apply_theme_overrides():
    scene = SceneV2(id=str(uuid.uuid4()))
    
    m1 = Material(id="m1", meta={"style_class": "shiny_metal"})
    scene.materials = [m1]
    
    theme = SceneTheme(
        name="MetalTheme",
        material_overrides={
            "shiny_metal": {
                "metallic": 1.0,
                "roughness": 0.1
            }
        }
    )
    
    apply_theme(scene, theme)
    
    assert m1.metallic == 1.0
    assert m1.roughness == 0.1
