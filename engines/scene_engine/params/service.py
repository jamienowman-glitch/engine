"""Param Engine Service."""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from engines.scene_engine.core.scene_v2 import SceneV2
from engines.scene_engine.core.geometry import Vector3
from engines.scene_engine.params.models import (
    ParamGraph, ParamNode, ParamNodeKind, ParamType, 
    ParamBinding, ParamTargetKind
)
from engines.scene_engine.avatar.style import AvatarStyleParams

# --- Evaluation Core ---


# --- Evaluation Core ---

def _ensure_list(val: Any) -> List[Any]:
    if isinstance(val, list):
        return val
    return [val]

def _match_lists(*args: Any) -> Tuple[List[Any], int]:
    """
    Expands inputs to lists of matching length (Longest List behavior).
    Returns (list_of_lists, max_length).
    """
    lists = [_ensure_list(x) for x in args]
    max_len = max(len(l) for l in lists)
    if max_len == 0:
        return [[] for _ in args], 0
        
    out_lists = []
    for l in lists:
        if len(l) == 0:
            out_lists.append([None] * max_len) # Should probably not happen if max > 0
        elif len(l) == 1:
            out_lists.append(l * max_len) # Repeat scalar
        elif len(l) < max_len:
            # Repeat last element? Or repeat cycle? 
            # Grasshopper usually repeats last. 
            last = l[-1]
            extended = l + [last] * (max_len - len(l))
            out_lists.append(extended)
        else:
            out_lists.append(l)
            
    return out_lists, max_len

def _eval_add(inputs: Dict[str, Any]) -> Any:
    # Supports float + float, or vector + vector, OR LISTS
    raw_a = inputs.get("a", 0.0)
    raw_b = inputs.get("b", 0.0)
    
    # If any is list, we map
    if isinstance(raw_a, list) or isinstance(raw_b, list):
        lists, count = _match_lists(raw_a, raw_b)
        res = []
        for i in range(count):
            res.append(_eval_add({"a": lists[0][i], "b": lists[1][i]}))
        return res

    a, b = raw_a, raw_b
    if isinstance(a, Vector3) and isinstance(b, Vector3):
        return a.add(b)
    
    # Simple float fallback
    return float(a) + float(b)

def _eval_multiply(inputs: Dict[str, Any]) -> Any:
    raw_a = inputs.get("a", 1.0)
    raw_b = inputs.get("b", 1.0)
    
    if isinstance(raw_a, list) or isinstance(raw_b, list):
        lists, count = _match_lists(raw_a, raw_b)
        res = []
        for i in range(count):
            res.append(_eval_multiply({"a": lists[0][i], "b": lists[1][i]}))
        return res
        
    a, b = raw_a, raw_b
    if isinstance(a, Vector3):
        s = float(b)
        return a.mul(s)
    
    return float(a) * float(b)

def _eval_remap(inputs: Dict[str, Any], params: Dict[str, Any]) -> Any:
    val = inputs.get("value", 0.0)
    # Check if list
    if isinstance(val, list):
        res = []
        for v in val:
            res.append(_eval_remap({"value": v}, params))
        return res
        
    v_float = float(val)
    in_min = float(params.get("in_min", 0.0))
    in_max = float(params.get("in_max", 1.0))
    out_min = float(params.get("out_min", 0.0))
    out_max = float(params.get("out_max", 1.0))
    
    if abs(in_max - in_min) < 1e-6:
        return out_min
        
    t = (v_float - in_min) / (in_max - in_min)
    return out_min + t * (out_max - out_min)

def _eval_clamp(inputs: Dict[str, Any], params: Dict[str, Any]) -> Any:
    val = inputs.get("value", 0.0)
    if isinstance(val, list):
        return [_eval_clamp({"value": v}, params) for v in val]
        
    c_min = float(params.get("min", 0.0))
    c_max = float(params.get("max", 1.0))
    return max(min(float(val), c_max), c_min)

def _eval_vector_compose(inputs: Dict[str, Any]) -> Any:
    rx = inputs.get("x", 0.0)
    ry = inputs.get("y", 0.0)
    rz = inputs.get("z", 0.0)
    
    if isinstance(rx, list) or isinstance(ry, list) or isinstance(rz, list):
        lists, count = _match_lists(rx, ry, rz)
        res = []
        for i in range(count):
             res.append(Vector3(x=float(lists[0][i]), y=float(lists[1][i]), z=float(lists[2][i])))
        return res

    return Vector3(x=float(rx), y=float(ry), z=float(rz))

# Generators

def _eval_grid_2d(params: Dict[str, Any]) -> List[Vector3]:
    # params: width, height, count_x, count_y
    w = float(params.get("width", 10.0))
    h = float(params.get("height", 10.0))
    cx = int(params.get("count_x", 5))
    cy = int(params.get("count_y", 5))
    
    pts = []
    # Centered grid
    start_x = -w / 2.0
    start_y = -h / 2.0
    
    step_x = w / max(1, cx - 1)
    step_y = h / max(1, cy - 1)
    
    for iy in range(cy):
        for ix in range(cx):
            pts.append(Vector3(
                x=start_x + ix * step_x, 
                y=0, 
                z=start_y + iy * step_y # Z is depth/height in 3D usually, or Y? 
                # Let's map Y to Z for ground. 
            ))
    return pts

def _eval_noise_1d(inputs: Dict[str, Any], params: Dict[str, Any]) -> Any:
    # 1D Perlin-ish or sine?
    # inputs: value (float or list)
    # params: scale
    scale = float(params.get("scale", 1.0))
    val = inputs.get("value", 0.0)
    
    def noise(x):
        import math
        return (math.sin(x * scale) + 1.0) * 0.5 # 0..1 sine wave approximation
        
    if isinstance(val, list):
        return [noise(float(v)) for v in val]
    return noise(float(val))

def _eval_random_float(params: Dict[str, Any]) -> List[float]:
    import random
    seed = int(params.get("seed", 0))
    count = int(params.get("count", 1))
    mn = float(params.get("min", 0.0))
    mx = float(params.get("max", 1.0))
    
    rng = random.Random(seed)
    return [rng.uniform(mn, mx) for _ in range(count)]


def evaluate_param_graph(
    graph: ParamGraph, 
    input_overrides: Dict[str, Any]
) -> Dict[str, Any]:
    
    computed = {} # node_id -> value
    
    for key, val in input_overrides.items():
        target_id = graph.exposed_inputs.get(key)
        if target_id:
            computed[target_id] = val

    node_map = {n.id: n for n in graph.nodes}
    
    # Visited set for cycle detection (primitive)
    visiting = set()

    def resolve(node_id: str):
        if node_id in computed:
            return computed[node_id]
        
        if node_id in visiting:
            return 0.0 # Cycle!
        visiting.add(node_id)
        
        node = node_map.get(node_id)
        if not node: 
            visiting.remove(node_id)
            return 0.0
        
        # Recursively resolve inputs
        resolved_inputs = {}
        for slot, source_id in node.inputs.items():
            resolved_inputs[slot] = resolve(source_id)
            
        # Compute
        val = None
        
        # --- Value Nodes ---
        if node.kind == ParamNodeKind.CONSTANT:
            val = node.params.get("value", 0.0)
        elif node.kind == ParamNodeKind.INPUT:
            val = node.params.get("default", 0.0)
            
        # --- Math Nodes ---
        elif node.kind == ParamNodeKind.ADD:
            val = _eval_add(resolved_inputs)
        elif node.kind == ParamNodeKind.MULTIPLY:
            val = _eval_multiply(resolved_inputs)
        elif node.kind == ParamNodeKind.REMAP:
            val = _eval_remap(resolved_inputs, node.params)
        elif node.kind == ParamNodeKind.CLAMP:
            val = _eval_clamp(resolved_inputs, node.params)
        elif node.kind == ParamNodeKind.VECTOR_COMPOSE:
            val = _eval_vector_compose(resolved_inputs)
            
        # --- Generators (Phase 6) ---
        elif node.kind == ParamNodeKind.GRID_2D:
            val = _eval_grid_2d(node.params)
        elif node.kind == ParamNodeKind.RANDOM_FLOAT:
            val = _eval_random_float(node.params)
        elif node.kind == ParamNodeKind.NOISE_1D:
            val = _eval_noise_1d(resolved_inputs, node.params)
            
        # --- Legacy ---
        elif node.kind == ParamNodeKind.SCRIPT_EXPR:
            expr = node.params.get("expression", "0")
            safe_scope = {"math": math}
            safe_scope.update(resolved_inputs)
            try:
                val = eval(expr, {"__builtins__": {}}, safe_scope)
            except:
                val = 0.0

        if val is None: val = 0.0
        
        computed[node_id] = val
        visiting.remove(node_id)
        return val

    # Resolve all outputs
    results = {}
    for out_name, node_id in graph.outputs.items():
        results[out_name] = resolve(node_id)
        
    return results


# --- Bindings ---

def apply_param_bindings(
    scene: SceneV2, 
    graph_results: Dict[str, Any], 
    bindings: List[ParamBinding]
) -> SceneV2:
    """Applies computed graph values to the scene properties."""
    
    # NOTE: If graph outputs Lists, we might need new Binding targets that accept lists (e.g. Instancer).
    # For Phase 6 binding updates are not explicitly requested, but we should handle robustness.
    # If a binding expects a float and gets a list, we take the first element?
    
    def _unwrap(v):
        if isinstance(v, list):
            return v[0] if v else 0.0
        return v
        
    # Helper recursive finder
    def _find_node(nodes, nid):
        for n in nodes:
            if n.id == nid: return n
            f = _find_node(n.children, nid)
            if f: return f
        return None

    mat_map = {m.id: m for m in scene.materials}
    
    for binding in bindings:
        raw_val = graph_results.get(binding.graph_output_name)
        if raw_val is None: continue
        
        # For now, standard bindings only support scalar/single updates.
        # Future phases (Instancing) will use Lists.
        val = _unwrap(raw_val)
        
        if binding.target_kind == ParamTargetKind.NODE_POSITION_Y:
            n = _find_node(scene.nodes, binding.target_id)
            if n: n.transform.position.y = float(val)

        elif binding.target_kind == ParamTargetKind.NODE_SCALE_UNIFORM:
            n = _find_node(scene.nodes, binding.target_id)
            if n:
                s = float(val)
                n.transform.scale = Vector3(x=s, y=s, z=s)

        elif binding.target_kind == ParamTargetKind.MATERIAL_COLOR:
            m = mat_map.get(binding.target_id)
            if m and isinstance(val, Vector3):
                 m.base_color = val
                    
        elif binding.target_kind == ParamTargetKind.CAMERA_DISTANCE:
            if scene.camera and scene.camera.target:
                t = scene.camera.target
                p = scene.camera.position
                dx = p.x - t.x
                dy = p.y - t.y
                dz = p.z - t.z
                dist = math.sqrt(dx*dx + dy*dy + dz*dz)
                if dist > 0:
                     ndist = float(val)
                     factor = ndist / dist
                     scene.camera.position = Vector3(
                         x=t.x + dx*factor,
                         y=t.y + dy*factor,
                         z=t.z + dz*factor
                     )

        elif binding.target_kind == ParamTargetKind.AVATAR_STYLE_FIELD:
             # Logic:
             # 1. Find style params locally (scene.nodes[0] meta or passed in?)
             # 2. Update value
             # 3. Call apply_avatar_style?
             # Problem: apply_avatar_style requires RigDefinition. We don't have it here.
             # Solution for P3: We just update the META params. 
             # The caller (Orchestrator) must re-run `apply_avatar_style` if they detect style changes.
             # OR we assume the Scene has RigDefinition stashed in meta?
             # Let's verify constraints: "Avatar Sliders".
             # If we only update meta, the view won't update.
             # But `apply_param_bindings` signature is `(SceneV2, ...) -> SceneV2`.
             # We can try to extract rig from scene if we stashed it?
             # Or we return scene with updated meta, and rely on the AvatarEditor loop to re-apply.
             # Let's stick to updating Meta for now, as re-applying full style (which rebuilds transforms)
             # is heavy and requires the Rig.
             
             if not scene.nodes: continue
             root = scene.nodes[0]
             style_data = root.meta.get("style_params", {})
             
             # Update field
             if binding.field_name:
                 style_data[binding.field_name] = val
                 root.meta["style_params"] = style_data
                 root.meta["dirty_style"] = True # Signal for re-application
                 
    return scene
