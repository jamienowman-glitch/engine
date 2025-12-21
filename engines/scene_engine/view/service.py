"""Service for 3D View & Selection Engine."""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from engines.scene_engine.core.geometry import EulerAngles, Mesh, Vector3
from engines.scene_engine.core.scene_v2 import SceneNodeV2, SceneV2
from engines.scene_engine.view.math_utils import (
    Matrix4,
    add,
    compose_trs,
    cross,
    dot,
    look_at,
    normalize,
    perspective,
    scale_vec,
    subtract,
)
from engines.scene_engine.view.models import (
    NodeViewInfo,
    PickNodeRequest,
    PickNodeResult,
    ViewAnalysisRequest,
    ViewAnalysisResult,
    ViewportSpec,
)


def _get_node_world_transform(node: SceneNodeV2, parent_transform: Matrix4 = None) -> Matrix4:
    # Convert Transform to Matrix
    # Convert degrees to radians for math_utils
    rot = node.transform.rotation
    rx, ry, rz = 0.0, 0.0, 0.0
    if isinstance(rot, EulerAngles):
        rx = math.radians(rot.x)
        ry = math.radians(rot.y)
        rz = math.radians(rot.z)
    # Quaternion support TODO: add if needed, defaulting to euler 0,0,0 if not euler
    
    local = compose_trs(
        node.transform.position,
        Vector3(x=rx, y=ry, z=rz),
        node.transform.scale
    )
    
    if parent_transform:
        return parent_transform * local
    return local


def _collect_renderbale_nodes(
    nodes: List[SceneNodeV2], 
    accum_transform: Matrix4, 
    flat_list: List[Tuple[SceneNodeV2, Matrix4]]
):
    for node in nodes:
        # P6: Visibility Check
        if node.meta.get("visible", True) is False:
            continue
            
        world = _get_node_world_transform(node, accum_transform)
        if node.mesh_id:
            flat_list.append((node, world))
        _collect_renderbale_nodes(node.children, world, flat_list)


def _build_camera_matrices(scene: SceneV2, viewport: ViewportSpec) -> Tuple[Matrix4, Matrix4, Vector3]:
    """Returns (ViewMatrix, ProjectionMatrix, CameraPos)."""
    eye = viewport.camera_position or Vector3(x=0, y=0, z=5)
    target = viewport.camera_target or Vector3(x=0, y=0, z=0)
    up = viewport.up
    
    # If using node transform
    if viewport.camera_node_id:
        # Find node
        # Simple scan
        found_node = None
        # We need full hierarchy search usually, or map
        # For P0 let's just do simple recursive search to key it
        # Actually we need the WORLD transform of the camera node.
        # This implies we need to traverse and find it.
        # To avoid double traversal, we could do one pass to find all world transforms.
        # But analyze_view is pure function. 
        # Let's just linearly search flat list if possible? 
        # No, tree is tree.
        pass # Only implementing explicit cam for now as P0 or simple root search

    view_mat = look_at(eye, target, up)
    proj_mat = perspective(
        viewport.fov_y_degrees, 
        viewport.aspect_ratio, 
        viewport.near, 
        viewport.far
    )
    return view_mat, proj_mat, eye


def analyze_view(req: ViewAnalysisRequest) -> ViewAnalysisResult:
    # 1. Setup Camera
    view_mat, proj_mat, cam_pos = _build_camera_matrices(req.scene, req.viewport)
    vp = req.viewport
    
    # 2. Collect nodes with transforms
    renderables: List[Tuple[SceneNodeV2, Matrix4]] = []
    _collect_renderbale_nodes(req.scene.nodes, Matrix4.identity(), renderables)
    
    # 3. Project
    results: List[NodeViewInfo] = []
    mesh_map: Dict[str, Mesh] = {m.id: m for m in req.scene.meshes}
    
    view_proj = proj_mat * view_mat
    
    for node, world_mat in renderables:
        mesh = mesh_map.get(node.mesh_id)
        if not mesh:
            continue
            
        # Transform bounds vertices (usually 8 corners)
        # Using mesh.vertices is expensive if high poly.
        # Use bounds if available.
        # Primitives usually have 8 vertices which is same as bounds.
        # If mesh has bounds_min/max, use those 8 corners.
        
        points_to_project = []
        if mesh.bounds_min and mesh.bounds_max:
            # Construct 8 corners
            min_v = mesh.bounds_min
            max_v = mesh.bounds_max
            points_to_project = [
                Vector3(x=min_v.x, y=min_v.y, z=min_v.z),
                Vector3(x=max_v.x, y=min_v.y, z=min_v.z),
                Vector3(x=max_v.x, y=max_v.y, z=min_v.z),
                Vector3(x=min_v.x, y=max_v.y, z=min_v.z),
                Vector3(x=min_v.x, y=min_v.y, z=max_v.z),
                Vector3(x=max_v.x, y=min_v.y, z=max_v.z),
                Vector3(x=max_v.x, y=max_v.y, z=max_v.z),
                Vector3(x=min_v.x, y=max_v.y, z=max_v.z),
            ]
        else:
            points_to_project = mesh.vertices[:8] # Fallback
            
        min_ndc_x, max_ndc_x = 1.0, -1.0
        min_ndc_y, max_ndc_y = 1.0, -1.0
        min_depth, max_depth = float('inf'), float('-inf')
        
        any_visible = False
        
        mvp = view_proj * world_mat
        
        for p in points_to_project:
            rx, ry, rz, rw = mvp.multiply_vector(p, 1.0)
            
            if rw != 0:
                nx = rx / rw
                ny = ry / rw
                nz = rz / rw
            else:
                nx, ny, nz = 0, 0, 0 # Singularity
            
            # Check frustum (NDC -1 to 1)
            # Actually we just track min/max and then check overlap
            # But simple check: if any point in range, or bounding box overlaps
            
            # Record depth (nz)
            # OpenGL NDC z is -1 to 1? or 0 to 1? usually -1 to 1.
            # Perspective divide done.
            
            # Screen space [0, 1] with 0,0 top-left?
            # NDC y is usually up.
            # Convert NDC to 0..1
            sx = (nx * 0.5) + 0.5
            sy = (1.0 - ((ny * 0.5) + 0.5)) # Flip Y for screen coords
            
            if sx < min_ndc_x: min_ndc_x = sx
            if sx > max_ndc_x: max_ndc_x = sx
            if sy < min_ndc_y: min_ndc_y = sy
            if sy > max_ndc_y: max_ndc_y = sy
            
            # Basic visibility check: is the point in front of camera?
            # w > 0 means in front
            if rw > 0 and -1 <= nx <= 1 and -1 <= ny <= 1 and -1 <= nz <= 1:
                any_visible = True
            
            # Avg depth calc? Use rw (linear-ish depth before divide) or nz (non-linear)
            # Use rw for sorting usually.
            if rw > 0:
                if rw < min_depth: min_depth = rw
        
        # If bounding box is valid
        if min_ndc_x <= max_ndc_x:
            # Check if off-screen
            # If max < 0 or min > 1 -> off screen
            if max_ndc_x < 0 or min_ndc_x > 1 or max_ndc_y < 0 or min_ndc_y > 1:
                any_visible = False

        if any_visible:
            # Clamp to 0-1 for cleanliness? Or keep off-screen bounds?
            # User output wants screen_bbox in [0, 1].
            # Let's clamp for output
            c_min_x = max(0.0, min(1.0, min_ndc_x))
            c_max_x = max(0.0, min(1.0, max_ndc_x))
            c_min_y = max(0.0, min(1.0, min_ndc_y))
            c_max_y = max(0.0, min(1.0, max_ndc_y))
            
            area = (c_max_x - c_min_x) * (c_max_y - c_min_y)
            
            results.append(NodeViewInfo(
                node_id=node.id,
                visible=True,
                screen_bbox=(min_ndc_x, min_ndc_y, max_ndc_x, max_ndc_y),
                screen_area_fraction=area,
                average_depth=min_depth if min_depth != float('inf') else 0.0,
                meta=node.meta
            ))
        else:
            # Not visible
            results.append(NodeViewInfo(
                node_id=node.id,
                visible=False,
                meta=node.meta
            ))

    return ViewAnalysisResult(nodes=results, meta={"count": len(results)})


def _ray_intersects_triangle(
    ray_origin: Vector3, 
    ray_dir: Vector3, 
    v0: Vector3, 
    v1: Vector3, 
    v2: Vector3
) -> Tuple[bool, float]:
    """Möller–Trumbore intersection algorithm."""
    epsilon = 0.0000001
    edge1 = subtract(v1, v0)
    edge2 = subtract(v2, v0)
    h = cross(ray_dir, edge2)
    a = dot(edge1, h)
    
    if -epsilon < a < epsilon:
        return False, 0.0 # Parallel
        
    f = 1.0 / a
    s = subtract(ray_origin, v0)
    u = f * dot(s, h)
    
    if u < 0.0 or u > 1.0:
        return False, 0.0
        
    q = cross(s, edge1)
    v = f * dot(ray_dir, q)
    
    if v < 0.0 or u + v > 1.0:
        return False, 0.0
        
    t = f * dot(edge2, q)
    
    if t > epsilon:
        return True, t
        
    return False, 0.0


def pick_node(req: PickNodeRequest) -> PickNodeResult:
    view_mat, proj_mat, cam_pos = _build_camera_matrices(req.scene, req.viewport)
    
    # Unproject screen point to ray
    # NDC
    ndc_x = (req.screen_x - 0.5) * 2.0
    ndc_y = (1.0 - req.screen_y - 0.5) * 2.0 # Flip Y back
    
    # Unprojection requires Inverse Matrix, which is heavy to implement manually perfectly.
    # Simple approach: 
    # Ray in View space:
    # tan(fov/2) stuff.
    
    aspect = req.viewport.aspect_ratio
    fov = math.radians(req.viewport.fov_y_degrees)
    
    # View space dir
    # px = ndc_x * aspect * tan(fov/2)
    # py = ndc_y * tan(fov/2)
    # pz = -1
    
    tan_half_fov = math.tan(fov / 2.0)
    vx = ndc_x * aspect * tan_half_fov
    vy = ndc_y * tan_half_fov
    vz = -1.0
    
    ray_dir_view = normalize(Vector3(x=vx, y=vy, z=vz))
    
    # Transform to World space using Inverse View Matrix
    # Inverse of LookAt is roughly Transpose of rotation + translation handling.
    # View Mat: [ R   T ]
    #           [ 0   1 ]
    # Inv:      [ R^T  -R^T * T ]
    # Since we have cam_pos separately, we can just rotate the ray direction by the camera's rotation.
    # The 'LookAt' constructs axes s (right), u (up), -f (view).
    # World Ray Dir = ray_dir_view.x * s + ray_dir_view.y * u + ray_dir_view.z * (-f)
    
    # Reconstruct axes matching look_at logic
    target = req.viewport.camera_target or Vector3(x=0, y=0, z=0)
    up = req.viewport.up
    f = normalize(subtract(target, cam_pos))
    s = normalize(cross(f, normalize(up)))
    u = cross(s, f)
    
    # Transform Dir
    # ray_view = (vx, vy, vz)
    # world = vx * s + vy * u + vz * (-f) -> wait, look_at defined -f as +Z in view space?
    # standard look_at puts camera looking down -Z.
    # So view direction is -Z.
    # Our simple projection assumed -1 Z.
    # So forward is f.
    
    # World Dir
    wd = add(add(scale_vec(s, vx), scale_vec(u, vy)), scale_vec(f, vz * -1.0)) # vz is -1, so f * 1
    # Check vz sign. In view space, looking down -Z. So forward is (0,0,-1).
    # f vector is Cam -> Target.
    # So (0,0,-1) view space should map to f world space.
    # (0,0,-1) is vx=0, vy=0, vz=-1.
    # Formula: vx*s + vy*u + (-vz)*f ? 
    # If vz=-1 -> 1*f. Correct.
    
    ray_dir_world = normalize(wd)
    ray_origin = cam_pos
    
    # Raycast scene
    renderables: List[Tuple[SceneNodeV2, Matrix4]] = []
    _collect_renderbale_nodes(req.scene.nodes, Matrix4.identity(), renderables)
    mesh_map = {m.id: m for m in req.scene.meshes}
    
    closest_t = float('inf')
    hit_node_id = None
    hit_pos = None
    # hit_normal = ... todo
    
    for node, world_mat in renderables:
        mesh = mesh_map.get(node.mesh_id)
        if not mesh:
            continue
            
        # Brute force triangles
        # indices assumed triangles
        if not mesh.indices:
            continue
            
        # Transform vertices to world once?
        # Or transform ray to model space? 
        # Transforming vertices to world is easier to reason about for P0 vs inverse matrix stability.
        # But inefficient. P0 says "brute force ok".
        
        world_verts = []
        for v in mesh.vertices:
            wx, wy, wz, ww = world_mat.multiply_vector(v, 1.0)
            world_verts.append(Vector3(x=wx, y=wy, z=wz))
            
        for i in range(0, len(mesh.indices), 3):
            if i + 2 >= len(mesh.indices):
                break
            i0, i1, i2 = mesh.indices[i], mesh.indices[i+1], mesh.indices[i+2]
            v0 = world_verts[i0]
            v1 = world_verts[i1]
            v2 = world_verts[i2]
            
            hit, t = _ray_intersects_triangle(ray_origin, ray_dir_world, v0, v1, v2)
            if hit and t < closest_t:
                closest_t = t
                hit_node_id = node.id
                # Calculate hit pos
                # P = O + tD
                hit_pos = add(ray_origin, scale_vec(ray_dir_world, t))
                
    return PickNodeResult(
        node_id=hit_node_id,
        hit_position=hit_pos,
        # hit_normal not implemented in P0 brute force unless requested for verification
        # The interface asks for it. Defaults to None.
    )
