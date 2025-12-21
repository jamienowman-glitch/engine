"""Avatar Lineage & Evolution Engine (P15)."""
from __future__ import annotations

import copy
import random
import uuid
from typing import Tuple, Optional

from engines.scene_engine.core.scene_v2 import SceneV2
from engines.scene_engine.avatar.models import AvatarRigDefinition
from engines.scene_engine.avatar.style import AvatarStyleParams, apply_avatar_style

def _perturb_value(val: float, rate: float, min_val: float, max_val: float) -> float:
    """Perturbs a float value by +/- rate (fraction of current or fixed steps?)."""
    # Simple perturbation: +/- rate * 10% of range? 
    # Or just +/- rate as absolute delta?
    # Let's assume rate is "intensity" 0.0-1.0.
    # We add a random delta up to +/- 0.1 * rate
    delta = (random.random() * 2.0 - 1.0) * 0.1 * rate
    new_val = val + delta
    return max(min_val, min(max_val, new_val))

def evolve_avatar(
    parent_scene: SceneV2, 
    parent_rig: AvatarRigDefinition, 
    mutation_rate: float = 0.1
) -> Tuple[SceneV2, AvatarRigDefinition]:
    """Creates a child avatar evolved from the parent."""
    
    # 1. Clone
    child_scene = SceneV2(id=str(uuid.uuid4()))
    child_scene.nodes = copy.deepcopy(parent_scene.nodes)
    child_scene.meshes = copy.deepcopy(parent_scene.meshes)
    child_scene.materials = copy.deepcopy(parent_scene.materials)
    # Copy other fields as needed
    
    child_rig = copy.deepcopy(parent_rig)
    
    # 2. Extract Genes (Style Params)
    # Assumes stored in root node meta as per variation.py
    # We might need to find the root node referenced by rig?
    # Or just use scene.nodes[0] if single avatar scene.
    # Default behavior:
    root_node = child_scene.nodes[0] # Simplification
    current_params_dict = root_node.meta.get("style_params")
    
    if current_params_dict:
        # Convert to model
        params = AvatarStyleParams(**current_params_dict)
        
        # 3. Mutate
        # Height: 1.5 - 2.1
        params.height = _perturb_value(params.height, mutation_rate, 1.5, 2.1)
        
        # Build: override floats if present, else ignore Enum for now
        if params.shoulder_width:
             params.shoulder_width = _perturb_value(params.shoulder_width, mutation_rate, 0.5, 2.0)
        
        if params.leg_length_ratio:
             params.leg_length_ratio = _perturb_value(params.leg_length_ratio, mutation_rate, 0.4, 0.6)
             
        # 4. Apply
        child_scene = apply_avatar_style(child_scene, child_rig, params)
        
    # 5. Lineage Metadata
    child_scene.meta["lineage"] = {
        "parent_id": parent_scene.id,
        "generation": parent_scene.meta.get("lineage", {}).get("generation", 0) + 1,
        "mutation_rate": mutation_rate
    }
    
    return child_scene, child_rig
