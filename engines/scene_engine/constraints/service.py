"""Constraint Solver Service."""
from __future__ import annotations

import math
import copy
from typing import Optional, List, Dict

from pydantic import BaseModel

from engines.scene_engine.core.scene_v2 import SceneV2, SceneNodeV2
from engines.scene_engine.core.geometry import Vector3, Quaternion, EulerAngles, Transform
from engines.scene_engine.constraints.models import SceneConstraint, ConstraintKind


class ConstraintSolverConfig(BaseModel):
    max_iterations: int = 10
    position_tolerance: float = 1e-3
    angle_tolerance_deg: float = 0.5


# --- Vector Math Helpers ---

def _v3_add(a: Vector3, b: Vector3) -> Vector3:
    return Vector3(x=a.x + b.x, y=a.y + b.y, z=a.z + b.z)

def _v3_sub(a: Vector3, b: Vector3) -> Vector3:
    return Vector3(x=a.x - b.x, y=a.y - b.y, z=a.z - b.z)

def _v3_scale(v: Vector3, s: float) -> Vector3:
    return Vector3(x=v.x * s, y=v.y * s, z=v.z * s)

def _v3_dot(a: Vector3, b: Vector3) -> float:
    return a.x * b.x + a.y * b.y + a.z * b.z

def _v3_length(v: Vector3) -> float:
    return math.sqrt(v.x*v.x + v.y*v.y + v.z*v.z)

def _v3_normalize(v: Vector3) -> Vector3:
    l = _v3_length(v)
    if l < 1e-6: return Vector3(x=0, y=0, z=0) # Safety
    return _v3_scale(v, 1.0/l)

def _v3_cross(a: Vector3, b: Vector3) -> Vector3:
    return Vector3(
        x=a.y * b.z - a.z * b.y,
        y=a.z * b.x - a.x * b.z,
        z=a.x * b.y - a.y * b.x
    )


# --- Node Access Helper ---
# V2 scenes might be flat or tree. We need a reliable node map.
# Ideally we flatten once.

def _get_node_map(scene: SceneV2) -> Dict[str, SceneNodeV2]:
    # Flatten
    mapping = {}
    def _traverse(nodes):
        for n in nodes:
            mapping[n.id] = n
            _traverse(n.children)
    _traverse(scene.nodes)
    return mapping


# --- Solver Logic ---

def solve_constraints(
    scene: SceneV2,
    config: Optional[ConstraintSolverConfig] = None,
) -> SceneV2:
    if config is None:
        config = ConstraintSolverConfig()

    # Work on a deep copy? 
    # Yes, function is pure.
    new_scene = copy.deepcopy(scene)
    if not new_scene.constraints:
        return new_scene
        
    node_map = _get_node_map(new_scene)
    
    # Iterative solver
    for iteration in range(config.max_iterations):
        total_correction = 0.0
        
        for c in new_scene.constraints:
            node = node_map.get(c.node_id)
            if not node: continue
            
            # --- ANCHOR_TO_NODE ---
            if c.kind == ConstraintKind.ANCHOR_TO_NODE:
                target_n = node_map.get(c.target_node_id)
                if target_n:
                    diff = _v3_sub(target_n.transform.position, node.transform.position)
                    if _v3_length(diff) > 1e-6:
                        node.transform.position = target_n.transform.position
                        total_correction += _v3_length(diff)

            # --- ANCHOR_TO_WORLD ---
            elif c.kind == ConstraintKind.ANCHOR_TO_WORLD:
                target = c.world_target
                if target:
                    # Correction
                    current = node.transform.position
                    diff = _v3_sub(target, current)
                    if _v3_length(diff) > 1e-6:
                        node.transform.position = target
                        total_correction += _v3_length(diff)
                        
            # --- KEEP_ON_PLANE ---
            elif c.kind == ConstraintKind.KEEP_ON_PLANE:
                normal = c.plane_normal or Vector3(x=0, y=1, z=0)
                offset = c.plane_offset or 0.0
                normal = _v3_normalize(normal)
                
                # dist = P . N - offset
                pos = node.transform.position
                dist = _v3_dot(pos, normal) - offset
                
                # Project back to plane: P' = P - dist * N
                if abs(dist) > config.position_tolerance:
                    correction = _v3_scale(normal, dist)
                    new_pos = _v3_sub(pos, correction)
                    node.transform.position = new_pos
                    total_correction += abs(dist)

            # --- MAINTAIN_DISTANCE ---
            elif c.kind == ConstraintKind.MAINTAIN_DISTANCE:
                target_node = node_map.get(c.target_node_id)
                if target_node:
                    required_dist = c.distance or 1.0
                    
                    p1 = node.transform.position
                    p2 = target_node.transform.position
                    
                    delta = _v3_sub(p1, p2)
                    current_dist = _v3_length(delta)
                    
                    if abs(current_dist - required_dist) > config.position_tolerance:
                        # Move p1 along line to satisfy distance
                        # If coincidental, choose Up
                        if current_dist < 1e-6:
                             dir_vec = Vector3(x=0, y=1, z=0)
                        else:
                             dir_vec = _v3_scale(delta, 1.0/current_dist)
                             
                        new_p1 = _v3_add(p2, _v3_scale(dir_vec, required_dist))
                        
                        # Apply
                        node.transform.position = new_p1
                        total_correction += abs(current_dist - required_dist)

            # --- AIM_AT_NODE ---
            elif c.kind == ConstraintKind.AIM_AT_NODE:
                # Rotation constraint
                # Logic: LookAt
                target_pos = None
                if c.target_node_id:
                    t_node = node_map.get(c.target_node_id)
                    if t_node: target_pos = t_node.transform.position
                elif c.world_target:
                    target_pos = c.world_target
                    
                if target_pos:
                    # Compute rotation to look at target
                    # We assume AIM implies +Z Forward? Or -Z? 
                    # Usually standard LOOKAT logic.
                    # Simple Euler: Atan2 logic.
                    # Or construct simple Quaternion logic if available.
                    # For P0, let's keep it very simple: update EulerAngles y (yaw) and x (pitch).
                    
                    eye = node.transform.position
                    target = target_pos
                    
                    # vector to target
                    fwd = _v3_sub(target, eye)
                    fwd = _v3_normalize(fwd)
                    
                    # Pitch/Yaw
                    # Yaw = atan2(x, z)
                    yaw = math.atan2(fwd.x, fwd.z)
                    
                    # Pitch = asin(y / length) -> -asin?
                    pitch = -math.asin(fwd.y) # Approximate
                    
                    # Apply
                    # Note: SceneV2 uses EulerAngles or Quaternion.
                    # If EulerAngles:
                    if isinstance(node.transform.rotation, EulerAngles):
                         node.transform.rotation.y = yaw
                         node.transform.rotation.x = pitch
                         node.transform.rotation.z = 0 # clear roll?
                    else:
                        # Quaternion TODO for P2
                        pass

        if total_correction < config.position_tolerance:
            break
            
    return new_scene


# --- In-Place Helper ---

def apply_constraints_in_place(
    scene: SceneV2,
    config: Optional[ConstraintSolverConfig] = None,
) -> SceneV2:
    """Mutates scene in place."""
    solved = solve_constraints(scene, config)
    
    # Sync transforms back
    # Since we deep copied, we need to map back by ID.
    target_map = _get_node_map(solved)
    
    def _sync(nodes):
        for n in nodes:
            solved_n = target_map.get(n.id)
            if solved_n:
                n.transform = solved_n.transform
            _sync(n.children)
            
    _sync(scene.nodes)
    return scene


# --- Management Helpers ---

def add_constraint(scene: SceneV2, constraint: SceneConstraint) -> SceneV2:
    # Ensure unique ID or replace?
    # Simple append
    scene.constraints.append(constraint)
    return scene 

def remove_constraint(scene: SceneV2, constraint_id: str) -> SceneV2:
    scene.constraints = [c for c in scene.constraints if c.id != constraint_id]
    return scene
