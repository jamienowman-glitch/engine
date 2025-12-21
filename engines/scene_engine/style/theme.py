"""Global Style & Brand Bible Engine (P14)."""
from __future__ import annotations

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from engines.scene_engine.core.scene_v2 import SceneV2
from engines.scene_engine.core.geometry import Vector3, Material

class ColorPalette(BaseModel):
    primary: Vector3 = Vector3(x=0.0, y=0.0, z=1.0) # Default Blue
    secondary: Vector3 = Vector3(x=1.0, y=0.0, z=0.0) # Red
    accent: Vector3 = Vector3(x=1.0, y=1.0, z=0.0) # Yellow
    background: Vector3 = Vector3(x=0.1, y=0.1, z=0.1) # Dark Grey
    text: Vector3 = Vector3(x=1.0, y=1.0, z=1.0) # White
    
    # Generic slots
    surface_1: Vector3 = Vector3(x=0.8, y=0.8, z=0.8)
    surface_2: Vector3 = Vector3(x=0.6, y=0.6, z=0.6)

class SceneTheme(BaseModel):
    name: str
    palette: ColorPalette = Field(default_factory=ColorPalette)
    
    # Mapping of style_class string to properties
    # e.g. "hero_prop" -> {"metallic": 1.0, "roughness": 0.2}
    material_overrides: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

def apply_theme(scene: SceneV2, theme: SceneTheme) -> SceneV2:
    """Applies the theme to the scene materials based on semantic tags."""
    
    # Helper to resolve color from palette by name
    def get_color(name: str) -> Optional[Vector3]:
        return getattr(theme.palette, name, None)

    for mat in scene.materials:
        # Check for semantic style class
        style_class = mat.meta.get("style_class")
        
        # 1. Apply Palette Colors
        # If the material name or style_class matches a palette key, apply it.
        # Priority: style_class -> material.name
        
        target_key = style_class if style_class else mat.name
        
        # Try to match palette field
        if hasattr(theme.palette, target_key):
             color = getattr(theme.palette, target_key)
             if isinstance(color, Vector3):
                 mat.base_color = color
        
        # 2. Apply Material Overrides
        if style_class and style_class in theme.material_overrides:
            overrides = theme.material_overrides[style_class]
            for k, v in overrides.items():
                if hasattr(mat, k):
                    setattr(mat, k, v)
                    
    return scene
