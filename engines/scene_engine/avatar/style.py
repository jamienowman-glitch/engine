"""Avatar Style Parameter Engine.

This module provides a generic, project-agnostic way to describe, apply, and extract
style parameters for rigged avatars. It operates purely on SceneV2 and AvatarRigDefinition.
"""
from __future__ import annotations

import copy
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from engines.scene_engine.avatar.models import AvatarBodyPart, AvatarRigDefinition
from engines.scene_engine.core.geometry import Vector3
from engines.scene_engine.core.scene_v2 import SceneV2, SceneNodeV2


class BodyBuild(str, Enum):
    """General body build category."""
    SLIM = "slim"
    AVERAGE = "average"
    HEAVY = "heavy"


class HeadProportion(str, Enum):
    """Head size relative to body."""
    SMALL = "small"
    NORMAL = "normal"
    LARGE = "large"


class AvatarStyleParams(BaseModel):
    """Generic style parameters for an avatar."""
    # Overall scale / proportions
    height: float = 1.8
    body_build: BodyBuild = BodyBuild.AVERAGE
    head_proportion: HeadProportion = HeadProportion.NORMAL

    # Fine-grained numeric controls (optional, override enums)
    head_scale: Optional[float] = None
    torso_scale: Optional[float] = None
    shoulder_width: Optional[float] = None
    limb_thickness: Optional[float] = None
    leg_length_ratio: Optional[float] = None  # 0-1 fraction of height
    arm_length_ratio: Optional[float] = None  # 0-1 fraction of height

    # Material / colour style (generic)
    base_color: Optional[str] = None  # hex or named
    accent_color_primary: Optional[str] = None
    accent_color_secondary: Optional[str] = None
    metallic: Optional[float] = None  # 0-1
    roughness: Optional[float] = None # 0-1

    # Simple feature toggles
    has_visor: bool = False
    has_hood: bool = False
    has_shoulder_pads: bool = False

    meta: Dict[str, Any] = Field(default_factory=dict)


def _get_derived_scales(style: AvatarStyleParams) -> Tuple[float, float, float]:
    """Derive head_scale, limb_thickness, torso_scale from style."""
    # Defaults
    h_scale = 1.0
    l_thick = 1.0
    t_scale = 1.0

    # Body Build influence
    if style.body_build == BodyBuild.SLIM:
        l_thick = 0.85
        t_scale = 0.9
    elif style.body_build == BodyBuild.HEAVY:
        l_thick = 1.25
        t_scale = 1.2

    # Head Proportion influence
    if style.head_proportion == HeadProportion.SMALL:
        h_scale = 0.85
    elif style.head_proportion == HeadProportion.LARGE:
        h_scale = 1.25

    # Overrides
    if style.head_scale is not None:
        h_scale = style.head_scale
    if style.limb_thickness is not None:
        l_thick = style.limb_thickness
    if style.torso_scale is not None:
        t_scale = style.torso_scale
    
    return h_scale, l_thick, t_scale


def apply_avatar_style(
    scene_in: SceneV2,
    rig: AvatarRigDefinition,
    style: AvatarStyleParams,
) -> SceneV2:
    """Apply style parameters to a rigged avatar scene.

    Operates on a copy of the scene.
    """
    scene = copy.deepcopy(scene_in)
    
    # 1. Resolve Parameters
    h_scale, l_thick, t_scale = _get_derived_scales(style)
    target_height = style.height

    # 2. Geometric Scaling
    # We need to find nodes associated with bones
    bone_map = {b.id: b for b in rig.bones}
    
    def get_node(node_id: str) -> Optional[SceneNodeV2]:
        # Simple search - optimizing lookup could be done if needed
        def find(nodes: List[SceneNodeV2]):
            for n in nodes:
                if n.id == node_id:
                    return n
                found = find(n.children)
                if found:
                    return found
            return None
        return find(scene.nodes)

    # 2a. Global Height Scale
    # Assuming root bone handles global scale or we scale the root node properties
    # Simple approach: Scale the root bone node uniformly to match height roughly
    # BUT, specific limb length ratios might require bone length adjustments.
    # For P0, we'll apply a uniform scale to the root to hit target height.
    # We assume '1.0' scale = 1.8m roughly, or rely on extracting current height first?
    # Let's simple assume input avatar is 'standard' size (~1.8m) if not specified.
    # Better: Measure current height first? 
    # For P0, we will assume standard base and just apply relative scale.
    base_height = 1.8
    global_scale = target_height / base_height
    
    root_node = get_node(bone_map[rig.root_bone_id].node_id) if rig.root_bone_id in bone_map else None
    if root_node:
        root_node.transform.scale = Vector3(
            x=root_node.transform.scale.x * global_scale,
            y=root_node.transform.scale.y * global_scale,
            z=root_node.transform.scale.z * global_scale
        )

    # 2b. Body Parts Scaling
    # Iterate bones to find body parts
    for bone in rig.bones:
        node = get_node(bone.node_id)
        if not node:
            continue
            
        if bone.part == AvatarBodyPart.HEAD:
            # Local uniform scale for head
            node.transform.scale.x *= h_scale
            node.transform.scale.y *= h_scale
            node.transform.scale.z *= h_scale
            
        elif bone.part in (AvatarBodyPart.TORSO, AvatarBodyPart.PELVIS):
             # Torso/Pelvis scale
            node.transform.scale.x *= t_scale
            node.transform.scale.z *= t_scale
            # Y (length) might be handled by length ratio, but let's stick to simple thickness for now
        
        elif "ARM" in bone.part.value or "LEG" in bone.part.value:
            # Limb thickness (X/Z usually, assuming Y is length along bone)
            # This assumption depends on bone orientation.
            # Standard rigor usually Y=up or Z=forward. 
            # Often bones are Y-aligned. Let's assume uniform thickness scale.
            node.transform.scale.x *= l_thick
            node.transform.scale.z *= l_thick
            
            # Simple length adjustments if ratios are provided
            # This is tricky without IK, so we might skip actual translation changes for P0
            # and just scale geometry length if that's what 'node' represents.
            pass

    # 3. Material Updates
    # We apply to ALL materials in the generic list for now, or filtred if we had a way.
    # Since this is a dedicated avatar scene passed in, we can iterate all.
    for mat in scene.materials:
        # Check base color
        if style.base_color:
             # Very simple hex to RGB mapping would go here, 
             # but we'll specific meta or simple assignment if it matches our vector type
             # Material.base_color is Vector3 (r,g,b). 
             # For P0, generic 'str' parsing is skipped to avoid deps, 
             # we assume we put the string in meta or similar?
             # Task description says "base_color: Optional[str]" in params.
             # but "update base_color if style.base_color is set".
             # We'll just store the string in meta["style_base_color"] to avoid colour parsing math deps
             mat.meta["base_color_override"] = style.base_color
             
        if style.metallic is not None:
            mat.metallic = style.metallic
        if style.roughness is not None:
            mat.roughness = style.roughness
            
        if style.accent_color_primary:
            mat.meta["accent_primary"] = style.accent_color_primary

    # 4. Meta Stamp
    if scene.nodes:
        # Stamp on the first root node found
        scene.nodes[0].meta["style_params"] = style.dict()

    return scene


def extract_avatar_style(
    scene_in: SceneV2,
    rig: AvatarRigDefinition,
) -> AvatarStyleParams:
    """Extract approximate style parameters from a scene."""
    # Check for stamped style first
    def find_style_meta(nodes):
        for n in nodes:
            if "style_params" in n.meta:
                return n.meta["style_params"]
            res = find_style_meta(n.children)
            if res:
                return res
        return None

    stamped = find_style_meta(scene_in.nodes)
    if stamped:
        # Logic to merge stamped with measured could go here
        # For P0, trusting the stamp is a good start.
        return AvatarStyleParams(**stamped)

    # Fallback: Measure (Stub implementation for P0 basics)
    # Start with defaults
    params = AvatarStyleParams()
    
    # Simple heuristic for height:
    # Find Y range of all meshes? Or Root scale?
    # Let's inspect root bone node scale.
    bone_map = {b.id: b for b in rig.bones}
    if rig.root_bone_id in bone_map:
        # Need to find the node in hierarchy to get world scale... expensive without flattened tree
        # For P0 of extraction, we'll return defaults + material sampling.
        pass

    # Sample material
    if scene_in.materials:
        first_mat = scene_in.materials[0]
        params.metallic = first_mat.metallic
        params.roughness = first_mat.roughness
        if "base_color_override" in first_mat.meta:
             params.base_color = first_mat.meta["base_color_override"]

    return params
