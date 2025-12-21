"""Builder for Scene V2 (Level B)."""
from __future__ import annotations

import uuid
from typing import List

from engines.scene_engine.core.geometry import (
    BoxParams,
    EulerAngles,
    Material,
    Mesh,
    PrimitiveKind,
    Transform,
    Vector3,
)
from engines.scene_engine.core.mapping import map_boxes
from engines.scene_engine.core.primitives import build_box_mesh
from engines.scene_engine.core.scene_v2 import (
    ConstructionOp,
    ConstructionOpKind,
    SceneGraphBuildRequest,
    SceneGraphBuildResult,
    SceneNodeV2,
    SceneV2,
)
from engines.scene_engine.core.types import Camera


def build_scene_v2(request: SceneGraphBuildRequest) -> SceneGraphBuildResult:
    # 1. Reuse existing V1 mapper to get layout positions
    v1_map_request = request.v1_request
    v1_nodes = map_boxes(v1_map_request.grid, v1_map_request.boxes, v1_map_request.recipe)

    # 2. Convert flat V1 nodes to V2 Scene structure
    nodes_v2: List[SceneNodeV2] = []
    meshes: List[Mesh] = []
    materials: List[Material] = []
    history: List[ConstructionOp] = []

    # Simple material for now
    default_mat = Material(id="mat_default", name="Default White", base_color=Vector3(x=1, y=1, z=1))
    materials.append(default_mat)

    for i, v1_node in enumerate(v1_nodes):
        # Create a unique mesh for each box size via Primitive Library
        # Optimize: reuse meshes for identical sizes? For P1, simple 1-to-1 is safer/easier.
        box_w = v1_node.gridBox3D.w
        box_h = v1_node.gridBox3D.h
        box_d = v1_node.gridBox3D.d
        
        box_params = BoxParams(width=box_w, height=box_h, depth=box_d)
        mesh = build_box_mesh(box_params)
        # Unique ID per instance for now to align with "primitive per node" history pattern
        mesh.id = f"mesh_{v1_node.id}"
        meshes.append(mesh)

        # Create Transform from worldPosition
        transform = Transform(
            position=Vector3(
                x=v1_node.worldPosition.x,
                y=v1_node.worldPosition.y,
                z=v1_node.worldPosition.z
            ),
            rotation=EulerAngles(x=0, y=0, z=0),
            scale=Vector3(x=1, y=1, z=1),
        )

        node_v2 = SceneNodeV2(
            id=v1_node.id,
            name=v1_node.meta.get("title") or f"Node_{v1_node.id}",
            transform=transform,
            mesh_id=mesh.id,
            material_id=default_mat.id,
            meta=v1_node.meta,
        )
        nodes_v2.append(node_v2)

        # History: Record CREATE_PRIMITIVE
        op_id = f"op_create_{v1_node.id}"
        op = ConstructionOp(
            id=op_id,
            kind=ConstructionOpKind.CREATE_PRIMITIVE,
            result_node_id=node_v2.id,
            params=box_params.model_dump(),
        )
        history.append(op)

    scene_v2 = SceneV2(
        id=uuid.uuid4().hex,
        nodes=nodes_v2,
        meshes=meshes,
        materials=materials,
        # camera=None,
        history=history,
    )

    return SceneGraphBuildResult(scene=scene_v2)

