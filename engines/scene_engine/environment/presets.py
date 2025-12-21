"""Environment & Light Presets (P8)."""
from __future__ import annotations

import uuid
from typing import List, Optional

from pydantic import BaseModel, Field

from engines.scene_engine.core.scene_v2 import SceneV2
from engines.scene_engine.core.geometry import Vector3
from engines.scene_engine.camera.models import Light, LightKind
from engines.scene_engine.environment.models import RoomParams
from engines.scene_engine.environment.service import build_room


class LightPreset(BaseModel):
    id: str
    lights: List[Light]
    ambient_color: Vector3 = Vector3(x=0.1, y=0.1, z=0.1)


class EnvironmentPreset(BaseModel):
    id: str
    name: str
    light_preset: LightPreset
    room_params: Optional[RoomParams] = None # If None, keeps existing or no room


# --- Standard Library ---

def _light(kind, pos, color, intensity=1.0, direction=None):
    return Light(
        id=f"light_{uuid.uuid4().hex[:8]}",
        kind=kind,
        position=pos,
        color=color,
        intensity=intensity,
        direction=direction
    )

STUDIO_NEUTRAL = EnvironmentPreset(
    id="studio_neutral",
    name="Studio Neutral",
    light_preset=LightPreset(
        id="lp_studio",
        lights=[
            _light(LightKind.DIRECTIONAL, Vector3(x=2, y=5, z=2), Vector3(x=1, y=0.98, z=0.95), 1.2, Vector3(x=-0.5, y=-1, z=-0.5)),
            _light(LightKind.DIRECTIONAL, Vector3(x=-2, y=3, z=1), Vector3(x=0.8, y=0.8, z=0.9), 0.6, Vector3(x=0.5, y=-0.5, z=-0.2))
        ],
        ambient_color=Vector3(x=0.2, y=0.2, z=0.2)
    ),
    room_params=None # Or simple floor
)

CYBERPUNK_NEON = EnvironmentPreset(
    id="cyberpunk_neon",
    name="Cyberpunk Neon",
    light_preset=LightPreset(
        id="lp_neon",
        lights=[
            _light(LightKind.POINT, Vector3(x=2, y=2, z=1), Vector3(x=1, y=0.0, z=0.8), 2.0), # Pink
            _light(LightKind.POINT, Vector3(x=-2, y=2, z=-1), Vector3(x=0.0, y=1.0, z=1.0), 2.0), # Cyan
            _light(LightKind.SPOT, Vector3(x=0, y=5, z=0), Vector3(x=0.5, y=0.0, z=1.0), 1.5, Vector3(x=0, y=-1, z=0)) # Blue top
        ],
        ambient_color=Vector3(x=0.05, y=0.0, z=0.1)
    )
)

PRESETS = {
    STUDIO_NEUTRAL.id: STUDIO_NEUTRAL,
    CYBERPUNK_NEON.id: CYBERPUNK_NEON
}

def apply_environment_preset(scene: SceneV2, preset_id: str) -> SceneV2:
    preset = PRESETS.get(preset_id)
    if not preset: return scene
    
    # 1. Apply Lights
    scene.lights = preset.light_preset.lights
    if not scene.environment: scene.environment = {}
    scene.environment["ambient_color"] = preset.light_preset.ambient_color.model_dump()
    
    # 2. Apply Room/Geometry Logic (Optional)
    if preset.room_params:
        # Rebuild layout?
        # Merging room logic is complex (replaces existing?).
        # For P8, we assume "Environment Kit" replaces the environment nodes.
        # Implementation: filter out old env nodes?
        # We rely on specific cleaning or just append for now.
        # Or better: `build_room` returns scenes.
        # We'll stick to lights for now unless params provided.
        pass
        
    return scene
