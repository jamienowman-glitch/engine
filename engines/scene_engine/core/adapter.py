"""Adapter for Scene V2 -> V1 compatibility (Level B)."""
from __future__ import annotations

from typing import Dict, List

from engines.scene_engine.core.geometry import PrimitiveKind
from engines.scene_engine.core.scene_v2 import SceneNodeV2, SceneV2
from engines.scene_engine.core.types import GridBox3D, Scene, SceneNode, WorldPosition


def scene_v2_to_scene(scene_v2: SceneV2) -> Scene:
    """Flatten a SceneV2 into a V1 Scene."""
    v1_nodes: List[SceneNode] = []

    # Map meshes by ID for quick lookup to get dimensions
    mesh_map = {m.id: m for m in scene_v2.meshes}

    # Recursive function to process nodes
    def _process_node(node: SceneNodeV2, parent_x: float, parent_y: float, parent_z: float):
        # Calculate world position (simple composition of translation only for now)
        # Full matrix math would be needed for rotation/scale inheritance,
        # but for this pass we assume simple translation hierarchy or flat input.
        wx = parent_x + node.transform.position.x
        wy = parent_y + node.transform.position.y
        wz = parent_z + node.transform.position.z

        # If node has a mesh, emit a V1 SceneNode
        if node.mesh_id:
            mesh = mesh_map.get(node.mesh_id)
            if mesh and mesh.primitive_source:
                p = mesh.primitive_source
                kind = "box_v2_adapted"
                w, h, d = 1.0, 1.0, 1.0
                
                if mesh.primitive_source.kind == PrimitiveKind.BOX:
                    w = getattr(p, "width", 1.0)
                    h = getattr(p, "height", 1.0)
                    d = getattr(p, "depth", 1.0)
                    kind = "box_v2_adapted"
                    
                elif mesh.primitive_source.kind == PrimitiveKind.SPHERE:
                    r = getattr(p, "radius", 0.5)
                    w = h = d = r * 2.0
                    kind = "sphere_v2_adapted"
                    
                elif mesh.primitive_source.kind == PrimitiveKind.CAPSULE or mesh.primitive_source.kind == PrimitiveKind.CYLINDER:
                    r = getattr(p, "radius", 0.5)
                    # For capsule, radiusTop/Bottom might differ, assume uniform for now or max
                    if hasattr(p, "radiusTop"): r = max(r, getattr(p, "radiusTop"))
                    
                    height = getattr(p, "length", getattr(p, "height", 1.0))
                    w = d = r * 2.0
                    h = height
                    kind = "cylinder_v2_adapted" # Use generic name for viewer

                v1_nodes.append(
                    SceneNode(
                        id=node.id,
                        kind=kind,
                        gridBox3D=GridBox3D(x=wx, y=wy, z=wz, w=w, h=h, d=d),
                        worldPosition=WorldPosition(x=wx, y=wy, z=wz),
                        meta=node.meta,
                    )
                )

        # Recurse children
        for child in node.children:
            _process_node(child, wx, wy, wz)

    # Start recursion
    for node in scene_v2.nodes:
        _process_node(node, 0.0, 0.0, 0.0)

    # Camera Conversion
    v1_cam = None
    if scene_v2.camera:
        # Convert V2 Camera to V1 Camera
        # V1: position: List[float], target: List[float], mode: str
        c = scene_v2.camera
        from engines.scene_engine.core.types import Camera as V1Camera
        v1_cam = V1Camera(
            position=[c.position.x, c.position.y, c.position.z],
            target=[c.target.x, c.target.y, c.target.z],
            mode=c.projection.value
        )
    
    # If no camera in V2, let V1 use default (or create default)
    if not v1_cam:
        from engines.scene_engine.core.types import Camera as V1Camera
        v1_cam = V1Camera()

    return Scene(
        sceneId=scene_v2.id,
        nodes=v1_nodes,
        camera=v1_cam
    )
