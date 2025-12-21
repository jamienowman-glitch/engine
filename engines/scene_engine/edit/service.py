"""Service for Scene Edit Engine (Level B)."""
from __future__ import annotations

import copy
import uuid
from typing import List, Optional

from engines.scene_engine.core.geometry import Mesh, PrimitiveKind, Vector3, Material
from engines.scene_engine.core.primitives import (
    build_box_mesh,
    build_capsule_mesh,
    build_cylinder_mesh,
    build_plane_mesh,
    build_sphere_mesh,
)
from engines.scene_engine.core.scene_v2 import (
    ConstructionOp,
    ConstructionOpKind,
    SceneNodeV2,
    SceneV2,
)
from engines.scene_engine.core.types import Camera
from engines.scene_engine.edit.models import (
    AddPrimitiveNodeCommand,
    AddPrimitiveNodeResult,
    CreateSceneCommand,
    CreateSceneResult,
    DeleteNodeCommand,
    DeleteNodeResult,
    SetNodeAttachmentsCommand,
    SetNodeAttachmentsResult,
    UpdateNodeMetaCommand,
    UpdateNodeMetaResult,
    UpdateNodeTransformCommand,
    UpdateNodeTransformResult,
)


def _deep_copy_scene(scene: SceneV2) -> SceneV2:
    """Deep copy a scene."""
    # Pydantic's copy() is shallow by default for mutable fields like lists/dicts if not using deep=True?
    # Actually model_copy(deep=True) is safer for nested models.
    # Or just use standard copy.deepcopy logic via Pydantic methods.
    # model_copy(update=..., deep=True) is available in V2.
    # To be explicitly safe across Pydantic versions/behaviors in this repo:
    # We can serialize/deserialize or use copy.deepcopy.
    # copy.deepcopy usually works fine on Pydantic models.
    return copy.deepcopy(scene)


def _find_node_recursive(nodes: List[SceneNodeV2], node_id: str) -> Optional[SceneNodeV2]:
    for node in nodes:
        if node.id == node_id:
            return node
        found = _find_node_recursive(node.children, node_id)
        if found:
            return found
    return None


def _find_node(scene: SceneV2, node_id: str) -> Optional[SceneNodeV2]:
    return _find_node_recursive(scene.nodes, node_id)


def _remove_node_recursive(nodes: List[SceneNodeV2], node_id: str) -> bool:
    """Remove node from list, return True if removed."""
    for i, node in enumerate(nodes):
        if node.id == node_id:
            nodes.pop(i)
            return True
        if _remove_node_recursive(node.children, node_id):
            return True
    return False


def create_scene(cmd: CreateSceneCommand) -> CreateSceneResult:
    if cmd.seed_from_scene:
        scene = _deep_copy_scene(cmd.seed_from_scene)
        # Apply overrides if provided? Command says "use this as starting scene".
        # Assuming we keep ID or generate new one?
        # "Create a new SceneV2... If cmd.seed_from_scene is provided: Make a deep copy"
        # Usually "Create" implies a NEW ID.
        scene.id = uuid.uuid4().hex
    else:
        scene = SceneV2(
            id=uuid.uuid4().hex,
            nodes=[],
            meshes=[],
            materials=[],
            # camera=None,
            history=[],
            environment={}
        )

    # Apply metadata
    if cmd.name:
        # SceneV2 doesn't have 'name' field, storing in meta per instructions
        if scene.environment is None:
            scene.environment = {}
        scene.environment.setdefault("meta", {})
        scene.environment["meta"]["name"] = cmd.name
        
    if cmd.tags:
        if scene.environment is None:
            scene.environment = {}
        scene.environment.setdefault("meta", {})
        scene.environment["meta"]["tags"] = cmd.tags

    if cmd.meta:
        if scene.environment is None:
            scene.environment = {}
        scene.environment.setdefault("meta", {})
        scene.environment["meta"].update(cmd.meta)

    return CreateSceneResult(scene=scene)


def add_primitive_node(cmd: AddPrimitiveNodeCommand) -> AddPrimitiveNodeResult:
    scene = _deep_copy_scene(cmd.scene)
    
    # 1. Build Mesh
    p = cmd.primitive
    if p.kind == PrimitiveKind.BOX:
        mesh = build_box_mesh(p)
    elif p.kind == PrimitiveKind.SPHERE:
        mesh = build_sphere_mesh(p)
    elif p.kind == PrimitiveKind.CYLINDER:
        mesh = build_cylinder_mesh(p)
    elif p.kind == PrimitiveKind.CAPSULE:
        mesh = build_capsule_mesh(p)
    elif p.kind == PrimitiveKind.PLANE:
        mesh = build_plane_mesh(p)
    else:
        # Fallback or error?
        raise ValueError(f"Unknown primitive kind: {p.kind}")
    
    # Deduplication check? pure functions -> simpler to just append unique ID
    # Use deterministic ID based on primitive? Or random?
    # Instruction says: "Append the mesh... (or reuse)"
    # Let's just append for now to be safe.
    mesh.id = f"mesh_{uuid.uuid4().hex[:8]}"
    scene.meshes.append(mesh)

    # 2. Material
    mat_id = None
    if cmd.material:
        # Check if material exists or add it
        # Simple dedupe by ID if provided, else add
        # We assume cmd.material is a full object to add
        scene.materials.append(cmd.material)
        mat_id = cmd.material.id

    # 3. Create Node
    node_id = uuid.uuid4().hex
    new_node = SceneNodeV2(
        id=node_id,
        transform=cmd.transform,
        mesh_id=mesh.id,
        material_id=mat_id,
        meta=cmd.meta,
        children=[],
        attachments=[]
    )

    # 4. Attach to hierarchy
    if cmd.parent_node_id:
        parent = _find_node(scene, cmd.parent_node_id)
        if not parent:
            raise ValueError(f"Parent node {cmd.parent_node_id} not found")
        parent.children.append(new_node)
    else:
        scene.nodes.append(new_node)

    # 5. History
    if scene.history is None:
        scene.history = []
    
    op_id = f"op_{uuid.uuid4().hex}"
    op = ConstructionOp(
        id=op_id,
        kind=ConstructionOpKind.CREATE_PRIMITIVE,
        result_node_id=node_id,
        params={
            "primitive": cmd.primitive.model_dump(),
            "transform": cmd.transform.model_dump(),
            "parent_id": cmd.parent_node_id
        }
    )
    scene.history.append(op)

    return AddPrimitiveNodeResult(scene=scene, node_id=node_id)


def update_node_transform(cmd: UpdateNodeTransformCommand) -> UpdateNodeTransformResult:
    scene = _deep_copy_scene(cmd.scene)
    node = _find_node(scene, cmd.node_id)
    if not node:
        raise ValueError(f"Node {cmd.node_id} not found")
    
    node.transform = cmd.transform
    
    # History
    if scene.history is None:
        scene.history = []
        
    op = ConstructionOp(
        id=f"op_{uuid.uuid4().hex}",
        kind=ConstructionOpKind.APPLY_TRANSFORM,
        result_node_id=cmd.node_id,
        params={"transform": cmd.transform.model_dump()}
    )
    scene.history.append(op)
    
    return UpdateNodeTransformResult(scene=scene)


def update_node_meta(cmd: UpdateNodeMetaCommand) -> UpdateNodeMetaResult:
    scene = _deep_copy_scene(cmd.scene)
    node = _find_node(scene, cmd.node_id)
    if not node:
        raise ValueError(f"Node {cmd.node_id} not found")
        
    node.meta.update(cmd.meta)
    
    return UpdateNodeMetaResult(scene=scene)


def set_node_attachments(cmd: SetNodeAttachmentsCommand) -> SetNodeAttachmentsResult:
    scene = _deep_copy_scene(cmd.scene)
    node = _find_node(scene, cmd.node_id)
    if not node:
        raise ValueError(f"Node {cmd.node_id} not found")
        
    node.attachments = cmd.attachments
    
    return SetNodeAttachmentsResult(scene=scene)


def delete_node(cmd: DeleteNodeCommand) -> DeleteNodeResult:
    scene = _deep_copy_scene(cmd.scene)
    
    removed = _remove_node_recursive(scene.nodes, cmd.node_id)
    if not removed:
        # Could just return scene if idempotent, but raising ensures caller knows
        # Raising ValueError for consistency with other ops finding nodes
        raise ValueError(f"Node {cmd.node_id} not found")
        
    # Optional history? 
    # Instruction says: "Optionally add a new ConstructionOpKind for deletion... record it"
    # We didn't define DELETE_NODE in ConstructionOpKind enum in previous step.
    # So we skip logic or add a generic 'APPLY_MODIFIER' with param 'delete'?
    # Or just skip since strict ENUM validation might fail.
    # Step 2 instructions said: "Optionally add a new ConstructionOpKind... if yes..."
    # I didn't add it in prior pass. I'll skip to adhere to strict types unless I modify models.
    # "Optionally add a new ConstructionOpKind... and record it." -> Implies I should modify models if I want to record it.
    # I won't modify models in this file, I'll stick to what exists.
    
    return DeleteNodeResult(scene=scene)
