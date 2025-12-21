"""Avatar Variation Engine (P10)."""
from __future__ import annotations

import random
from typing import Dict, Any, Optional

from engines.scene_engine.core.scene_v2 import SceneV2
from engines.scene_engine.avatar.models import AvatarRigDefinition
from engines.scene_engine.avatar.style import AvatarStyleParams, apply_avatar_style

def generate_random_style(seed: Any) -> AvatarStyleParams:
    rng = random.Random(str(seed))
    
    # Height: 1.5m to 2.1m
    height = 1.5 + (rng.random() * 0.6)
    
    # Proportions
    # Shoulder width: 0.8 to 1.5
    shoulder_width = 0.8 + (rng.random() * 0.7)
    # Hip width (not directly in StyleParams, maybe use torso_scale?)
    # Using torso_scale as proxy for build which affects hip width implicitly via t_scale in apply_style.
    # We'll set generic params.
    
    # Leg length ratio: 0.45 to 0.55 of height
    leg_len = 0.45 + (rng.random() * 0.1)
    
    return AvatarStyleParams(
        height=height,
        shoulder_width=shoulder_width,
        leg_length_ratio=leg_len,
        torso_scale=0.9 + (rng.random() * 0.3), # 0.9-1.2
        limb_thickness=0.8 + (rng.random() * 0.5) # 0.8-1.3
    )


def randomize_avatar(scene: SceneV2, rig: AvatarRigDefinition, seed: Any) -> SceneV2:
    style = generate_random_style(seed)
    # Apply style
    # apply_avatar_style returns (new_scene, new_rig) usually?
    # Checking `avatar/style.py` signature:
    # `def apply_avatar_style(scene: SceneV2, rig_def: AvatarRigDefinition, params: AvatarStyleParams) -> SceneV2:`
    
    return apply_avatar_style(scene, rig, style)
