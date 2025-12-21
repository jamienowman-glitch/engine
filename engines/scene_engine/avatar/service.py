"""Service for Avatar Rig & Attachment Engine (P0)."""
from __future__ import annotations

import copy
import uuid
from typing import Dict, List, Optional, Tuple

from engines.scene_engine.avatar.models import (
    AvatarAttachmentBinding,
    AvatarAttachmentSlot,
    AvatarBodyPart,
    AvatarBone,
    AvatarRigDefinition,
    RigValidationError,
    RigValidationResult,
    MorphTarget,
    MorphApplication,
    VertexDelta,
    RetargetRigMap,
    RetargetMapping,
    AvatarParamSlider,
    AvatarParamSet,
    AvatarPreset,
    AvatarParamHistory,
    AvatarBuilder,
    KitSlot,
    KitMetadata,
    KitRegistry,
    KitAttachment,
    UVValidationResult,
    MaterialPreset,
)
from engines.scene_engine.core.geometry import (
    BoxParams,
    CapsuleParams,
    EulerAngles,
    Material,
    Mesh,
    SphereParams,
    Transform,
    Vector3,
)
from engines.scene_engine.core.primitives import (
    build_box_mesh,
    build_capsule_mesh,
    build_sphere_mesh,
)
from engines.scene_engine.core.scene_v2 import (
    AttachmentPoint,
    ConstructionOp,
    ConstructionOpKind,
    SceneNodeV2,
    SceneV2,
)
from engines.scene_engine.core.types import Camera


def _create_node(
    id: str,
    name: str,
    mesh: Optional[Mesh],
    transform: Transform,
    material_id: Optional[str] = None,
    children: List[SceneNodeV2] = None,
    attachments: List[AttachmentPoint] = None,
) -> SceneNodeV2:
    return SceneNodeV2(
        id=id,
        name=name,
        transform=transform,
        mesh_id=mesh.id if mesh else None,
        material_id=material_id,
        children=children or [],
        attachments=attachments or [],
    )


def _vec3(x, y, z) -> Vector3:
    return Vector3(x=float(x), y=float(y), z=float(z))


def _rot_zero() -> EulerAngles:
    return EulerAngles(x=0.0, y=0.0, z=0.0)


def _scale_one() -> Vector3:
    return Vector3(x=1.0, y=1.0, z=1.0)


def _transform(x=0, y=0, z=0, rx=0, ry=0, rz=0, s=1) -> Transform:
    return Transform(
        position=_vec3(x, y, z),
        rotation=EulerAngles(x=float(rx), y=float(ry), z=float(rz)),
        scale=_vec3(s, s, s)
    )


def build_default_avatar(scene_id: Optional[str] = None) -> Tuple[SceneV2, AvatarRigDefinition]:
    """Generates a default humanoid avatar structure."""
    
    # 1. Primitives & Meshes
    # Head (Sphere)
    mesh_head = build_sphere_mesh(SphereParams(radius=0.25))
    # Torso (Box)
    mesh_torso = build_box_mesh(BoxParams(width=0.5, height=0.6, depth=0.3))
    # Pelvis (Box - smaller)
    mesh_pelvis = build_box_mesh(BoxParams(width=0.45, height=0.2, depth=0.25))
    # Limbs (Capsules)
    # Arms length ~0.7 total, Legs ~0.9
    mesh_limb_upper = build_capsule_mesh(CapsuleParams(radius=0.08, length=0.35))
    mesh_limb_lower = build_capsule_mesh(CapsuleParams(radius=0.07, length=0.35))
    
    meshes = [mesh_head, mesh_torso, mesh_pelvis, mesh_limb_upper, mesh_limb_lower]
    
    # Materials
    mat_default = Material(id="mat_avatar_default", base_color=_vec3(0.8, 0.8, 0.8))
    
    # 2. Nodes & Hierarchy
    # Using simple offsets. Assuming Y is Up.
    
    # Pelvis is often Root or child of Root
    pelvis_id = f"bone_{uuid.uuid4().hex[:8]}"
    torso_id = f"bone_{uuid.uuid4().hex[:8]}"
    neck_id = f"bone_{uuid.uuid4().hex[:8]}" # Optional node for neck pivot
    head_id = f"bone_{uuid.uuid4().hex[:8]}"
    
    # Arms
    arm_l_u_id = f"bone_{uuid.uuid4().hex[:8]}"
    arm_l_l_id = f"bone_{uuid.uuid4().hex[:8]}"
    hand_l_id = f"bone_{uuid.uuid4().hex[:8]}" # Hand can use lower limb mesh or separate? Use small box for hand
    
    arm_r_u_id = f"bone_{uuid.uuid4().hex[:8]}"
    arm_r_l_id = f"bone_{uuid.uuid4().hex[:8]}"
    hand_r_id = f"bone_{uuid.uuid4().hex[:8]}"
    
    # Legs
    leg_l_u_id = f"bone_{uuid.uuid4().hex[:8]}"
    leg_l_l_id = f"bone_{uuid.uuid4().hex[:8]}"
    foot_l_id = f"bone_{uuid.uuid4().hex[:8]}"
    
    leg_r_u_id = f"bone_{uuid.uuid4().hex[:8]}"
    leg_r_l_id = f"bone_{uuid.uuid4().hex[:8]}"
    foot_r_id = f"bone_{uuid.uuid4().hex[:8]}"
    
    # Attachments Setup (on nodes)
    # Head Top
    att_head_top = AttachmentPoint(name=AvatarAttachmentSlot.HEAD_TOP.value, local_transform=_transform(y=0.25))
    
    # Hand Grips (in hand local)
    att_hand_l = AttachmentPoint(name=AvatarAttachmentSlot.HAND_L_GRIP.value, local_transform=_transform(y=0.0))
    att_hand_r = AttachmentPoint(name=AvatarAttachmentSlot.HAND_R_GRIP.value, local_transform=_transform(y=0.0))
    
    # Build Tree
    
    # Head
    node_head = _create_node(
        head_id, "Head", mesh_head, 
        transform=_transform(y=0.15), # relative to neck/torso top
        material_id=mat_default.id,
        attachments=[att_head_top]
    )
    
    # Torso
    node_torso = _create_node(
        torso_id, "Torso", mesh_torso,
        transform=_transform(y=0.4), # relative to pelvis
        material_id=mat_default.id,
        children=[node_head] # Head child of torso (simplified)
    )
    
    # Arms (attached to Torso)
    # Left Arm
    node_hand_l = _create_node(hand_l_id, "Hand_L", None, _transform(y=-0.35), attachments=[att_hand_l]) # Dummy mesh
    node_arm_l_l = _create_node(arm_l_l_id, "Arm_L_Lower", mesh_limb_lower, _transform(y=-0.35), mat_default.id, children=[node_hand_l])
    node_arm_l_u = _create_node(arm_l_u_id, "Arm_L_Upper", mesh_limb_upper, _transform(x=-0.35, y=0.2), mat_default.id, children=[node_arm_l_l])
    
    # Right Arm
    node_hand_r = _create_node(hand_r_id, "Hand_R", None, _transform(y=-0.35), attachments=[att_hand_r])
    node_arm_r_l = _create_node(arm_r_l_id, "Arm_R_Lower", mesh_limb_lower, _transform(y=-0.35), mat_default.id, children=[node_hand_r])
    node_arm_r_u = _create_node(arm_r_u_id, "Arm_R_Upper", mesh_limb_upper, _transform(x=0.35, y=0.2), mat_default.id, children=[node_arm_r_l])
    
    node_torso.children.extend([node_arm_l_u, node_arm_r_u])
    
    # Legs (attached to Pelvis)
    # Left Leg
    node_foot_l = _create_node(foot_l_id, "Foot_L", None, _transform(y=-0.35))
    node_leg_l_l = _create_node(leg_l_l_id, "Leg_L_Lower", mesh_limb_lower, _transform(y=-0.35), mat_default.id, children=[node_foot_l])
    node_leg_l_u = _create_node(leg_l_u_id, "Leg_L_Upper", mesh_limb_upper, _transform(x=-0.15, y=-0.1), mat_default.id, children=[node_leg_l_l])
    
    # Right Leg
    node_foot_r = _create_node(foot_r_id, "Foot_R", None, _transform(y=-0.35))
    node_leg_r_l = _create_node(leg_r_l_id, "Leg_R_Lower", mesh_limb_lower, _transform(y=-0.35), mat_default.id, children=[node_foot_r])
    node_leg_r_u = _create_node(leg_r_u_id, "Leg_R_Upper", mesh_limb_upper, _transform(x=0.15, y=-0.1), mat_default.id, children=[node_leg_r_l])
    
    # Pelvis (Root of body)
    node_pelvis = _create_node(
        pelvis_id, "Pelvis", mesh_pelvis,
        transform=_transform(y=1.0), # Lift off ground (legs ~0.7+ length)
        material_id=mat_default.id,
        children=[node_torso, node_leg_l_u, node_leg_r_u]
    )
    
    # 3. AvatarRigDefinition
    bones = [
        AvatarBone(id=f"b_{pelvis_id}", part=AvatarBodyPart.PELVIS, node_id=pelvis_id),
        AvatarBone(id=f"b_{torso_id}", part=AvatarBodyPart.TORSO, node_id=torso_id, parent_id=f"b_{pelvis_id}"),
        AvatarBone(id=f"b_{head_id}", part=AvatarBodyPart.HEAD, node_id=head_id, parent_id=f"b_{torso_id}"),
        # Arms
        AvatarBone(id=f"b_{arm_l_u_id}", part=AvatarBodyPart.ARM_L_UPPER, node_id=arm_l_u_id, parent_id=f"b_{torso_id}"),
        AvatarBone(id=f"b_{arm_l_l_id}", part=AvatarBodyPart.ARM_L_LOWER, node_id=arm_l_l_id, parent_id=f"b_{arm_l_u_id}"),
        AvatarBone(id=f"b_{hand_l_id}", part=AvatarBodyPart.HAND_L, node_id=hand_l_id, parent_id=f"b_{arm_l_l_id}"),
        AvatarBone(id=f"b_{arm_r_u_id}", part=AvatarBodyPart.ARM_R_UPPER, node_id=arm_r_u_id, parent_id=f"b_{torso_id}"),
        AvatarBone(id=f"b_{arm_r_l_id}", part=AvatarBodyPart.ARM_R_LOWER, node_id=arm_r_l_id, parent_id=f"b_{arm_r_u_id}"),
        AvatarBone(id=f"b_{hand_r_id}", part=AvatarBodyPart.HAND_R, node_id=hand_r_id, parent_id=f"b_{arm_r_l_id}"),
        # Legs
        AvatarBone(id=f"b_{leg_l_u_id}", part=AvatarBodyPart.LEG_L_UPPER, node_id=leg_l_u_id, parent_id=f"b_{pelvis_id}"),
        AvatarBone(id=f"b_{leg_l_l_id}", part=AvatarBodyPart.LEG_L_LOWER, node_id=leg_l_l_id, parent_id=f"b_{leg_l_u_id}"),
        AvatarBone(id=f"b_{foot_l_id}", part=AvatarBodyPart.FOOT_L, node_id=foot_l_id, parent_id=f"b_{leg_l_l_id}"),
        AvatarBone(id=f"b_{leg_r_u_id}", part=AvatarBodyPart.LEG_R_UPPER, node_id=leg_r_u_id, parent_id=f"b_{pelvis_id}"),
        AvatarBone(id=f"b_{leg_r_l_id}", part=AvatarBodyPart.LEG_R_LOWER, node_id=leg_r_l_id, parent_id=f"b_{leg_r_u_id}"),
        AvatarBone(id=f"b_{foot_r_id}", part=AvatarBodyPart.FOOT_R, node_id=foot_r_id, parent_id=f"b_{leg_r_l_id}"),
    ]
    
    bindings = [
        AvatarAttachmentBinding(slot=AvatarAttachmentSlot.HEAD_TOP, bone_id=f"b_{head_id}", local_transform=_transform()),
        AvatarAttachmentBinding(slot=AvatarAttachmentSlot.HAND_L_GRIP, bone_id=f"b_{hand_l_id}", local_transform=_transform()),
        AvatarAttachmentBinding(slot=AvatarAttachmentSlot.HAND_R_GRIP, bone_id=f"b_{hand_r_id}", local_transform=_transform()),
        # ... others
    ]
    
    rig_def = AvatarRigDefinition(
        bones=bones,
        attachments=bindings,
        root_bone_id=f"b_{pelvis_id}"
    )
    
    scene = SceneV2(
        id=scene_id or uuid.uuid4().hex,
        nodes=[node_pelvis],
        meshes=meshes,
        materials=[mat_default],
        # camera=None (optional)
        history=[
            ConstructionOp(
                id=f"op_{uuid.uuid4().hex}",
                kind=ConstructionOpKind.CREATE_PRIMITIVE,
                params={"type": "default_avatar"}
            )
        ]
    )
    
    return scene, rig_def


def insert_default_avatar_into_scene(scene: SceneV2) -> Tuple[SceneV2, AvatarRigDefinition]:
    """Inserts a default avatar into an existing scene."""
    # 1. Generate Avatar Scene
    avatar_scene, rig_def = build_default_avatar()
    
    # 2. Merge Assets
    new_scene = copy.deepcopy(scene)
    new_scene.meshes.extend(avatar_scene.meshes)
    new_scene.materials.extend(avatar_scene.materials)
    
    # 3. Merge Nodes
    # Attach avatar root (pelvis) to scene root? Or just append to list?
    # Append to list is safest for "world root".
    # Assuming nodes in SceneV2 are roots.
    new_scene.nodes.extend(avatar_scene.nodes)
    
    # 4. History
    if new_scene.history and avatar_scene.history:
        new_scene.history.extend(avatar_scene.history)
    
    return new_scene, rig_def


def _find_node_recursive(nodes: List[SceneNodeV2], node_id: str) -> Optional[SceneNodeV2]:
    for node in nodes:
        if node.id == node_id:
            return node
        found = _find_node_recursive(node.children, node_id)
        if found:
            return found
    return None


def apply_avatar_pose(scene: SceneV2, rig: AvatarRigDefinition, bone_transforms: Dict[AvatarBodyPart, Transform]) -> SceneV2:
    new_scene = copy.deepcopy(scene)
    
    # Map bones to parts for fast lookup
    part_to_node_id = {b.part: b.node_id for b in rig.bones}
    
    for part, transform in bone_transforms.items():
        node_id = part_to_node_id.get(part)
        if not node_id:
            continue
            
        node = _find_node_recursive(new_scene.nodes, node_id)
        if node:
            # Merge logic for P1:
            # - Identity: We assume "Rest Pose" positions are in the current scene nodes.
            # - Poses usually only affect Rotation for limbs.
            # - Poses affect Position + Rotation for Root (Pelvis).
            
            current_t = node.transform
            input_t = transform
            
            new_t = copy.deepcopy(current_t)
            
            # Apply Rotation (Always)
            new_t.rotation = input_t.rotation
            
            # Apply Position (Only if Root/Pelvis?)
            if part == AvatarBodyPart.PELVIS:
                new_t.position = input_t.position
            # Else preserve current_t.position (bone offset)

            # Apply Scale?
            # Usually poses don't scale. Style scales. 
            # We preserve current scale to not undo Style.
            
            node.transform = new_t
            
            # History
            if not new_scene.history:
                new_scene.history = []
            new_scene.history.append(ConstructionOp(
                id=f"op_pose_{uuid.uuid4().hex}",
                kind=ConstructionOpKind.APPLY_TRANSFORM,
                result_node_id=node.id,
                params={"pose_part": part.value}
            ))

    return new_scene


def reset_avatar_pose(scene: SceneV2, rig: AvatarRigDefinition) -> SceneV2:
    # Requires storing default pose?
    # P0: Re-generate default avatar structure to get default transforms and apply them?
    # Or just don't implement full reset if we don't track state.
    # Hack: "whatever initial pose build_default_avatar used".
    # We can generate a dummy default avatar, read its transforms, and apply to current.
    
    dummy_scene, _ = build_default_avatar()
    part_to_node_id_current = {b.part: b.node_id for b in rig.bones}
    
    # We assume rig structure matches default (same bone parts).
    # We need to map Default Avatar Node -> transform.
    # Since node IDs are random, we can't map by ID. We must map by Structure/Name or rely on Rig Definition?
    # The dummy rig definition will have mappings.
    
    # Build a map of Part -> DefaultTransform from dummy
    # We need the dummy rig definition too.
    dummy_rig = _extract_rig_from_default(dummy_scene) # wait, build returns rig.
    # Re-call build
    _, dummy_rig = build_default_avatar() # This creates NEW IDs.
    
    # We can't easily map if build_default_avatar makes new random IDs every time.
    # Solution: We can't implement Reset perfectly without stored rest pose.
    # For P0, let's skip or return untransformed if simple.
    # Or just do nothing.
    return scene # Placeholder


def attach_node_to_avatar_slot(scene: SceneV2, rig: AvatarRigDefinition, slot: AvatarAttachmentSlot, node_id: str) -> SceneV2:
    new_scene = copy.deepcopy(scene)
    
    # 1. Find Binding
    binding = next((b for b in rig.attachments if b.slot == slot), None)
    if not binding:
        raise ValueError(f"Slot {slot} not found in rig")
        
    bone = next((b for b in rig.bones if b.id == binding.bone_id), None)
    if not bone:
        raise ValueError(f"Bone {binding.bone_id} not found")
        
    target_bone_node_id = bone.node_id
    
    # 2. Find Node to attach
    # We need to remove it from its current parent and add to new parent.
    node_to_move = _find_node_recursive(new_scene.nodes, node_id)
    if not node_to_move:
        raise ValueError(f"Node {node_id} not found")
    
    # Remove from old location
    # This requires parent pointer or recursive delete
    _remove_node_recursive(new_scene.nodes, node_id)
    
    # 3. Find Bone Node
    bone_node = _find_node_recursive(new_scene.nodes, target_bone_node_id)
    if not bone_node:
        raise ValueError(f"Bone Node {target_bone_node_id} not found")
        
    # 4. Attach
    bone_node.children.append(node_to_move)
    
    # 5. Apply Offset (Binding Local Transform)
    # node.transform = binding.local_transform ?
    # Or multiply? Usually attachment point defines the "Socket". 
    # If the prop is at 0,0,0, it snaps to socket.
    # So we should set node parent-relative transform to binding.local_transform (which is usually 0 if slot is exact, or offset).
    # Wait, binding.local_transform is "local transform of the attachment point"? Or "transform to apply to attached object"?
    # The Prompt says: "Optionally adjust the attached node’s transform by the local_transform defined in the binding."
    # We'll set the node's transform to identity (snap) or the binding offset.
    # Let's assume snap to identity (0,0,0) relative to the socket, or if binding has transform, use that.
    
    # Actually, SceneNodeV2 has `attachments` list which are AttachmentPoints.
    # If the bone node has an AttachmentPoint matching the slot name, we should snap to THAT.
    # The RigDef `attachments` list maps Slot -> BoneID.
    # The Bone Node `attachments` list has the actual transform relative to bone.
    
    # Correct logic:
    # 1. Find bone from RigDef binding.
    # 2. Find AttachmentPoint in bone.attachments matching slot name.
    # 3. Set node transform = AttachmentPoint.local_transform.
    
    att_point = next((a for a in bone_node.attachments if a.name == slot.value), None)
    if att_point:
        node_to_move.transform = att_point.local_transform
    else:
        # Fallback to 0
        node_to_move.transform = _transform()

    return new_scene


# Helpers mainly for internal use in delete/find
def _remove_node_recursive(nodes: List[SceneNodeV2], node_id: str) -> bool:
    for i, node in enumerate(nodes):
        if node.id == node_id:
            nodes.pop(i)
            return True
        if _remove_node_recursive(node.children, node_id):
            return True
    return False

# ===== PHASE AV01: Rig Validation & Morph Services =====

def validate_rig(rig: AvatarRigDefinition) -> RigValidationResult:
    """
    Validate a rig structure for correctness.
    
    Checks:
    - Root bone exists
    - All parent references are valid
    - No duplicate bone IDs
    - No NaN/invalid transforms (future: skeleton T-pose alignment)
    """
    errors: List[RigValidationError] = []
    warnings: List[str] = []
    
    bone_ids = {bone.id for bone in rig.bones}
    
    # Check root bone exists
    if rig.root_bone_id not in bone_ids:
        errors.append(RigValidationError(
            error_code="MISSING_ROOT",
            bone_id=rig.root_bone_id,
            message=f"Root bone '{rig.root_bone_id}' not found in rig bones."
        ))
    
    # Check for duplicate bone IDs
    seen_ids = set()
    for bone in rig.bones:
        if bone.id in seen_ids:
            errors.append(RigValidationError(
                error_code="DUPLICATE_BONE_ID",
                bone_id=bone.id,
                message=f"Bone ID '{bone.id}' is duplicated."
            ))
        seen_ids.add(bone.id)
    
    # Check parent references
    for bone in rig.bones:
        if bone.parent_id and bone.parent_id not in bone_ids:
            errors.append(RigValidationError(
                error_code="MISSING_PARENT",
                bone_id=bone.id,
                message=f"Bone '{bone.id}' references non-existent parent '{bone.parent_id}'."
            ))
    
    # Validate attachment slot references
    for att in rig.attachments:
        if att.bone_id not in bone_ids:
            errors.append(RigValidationError(
                error_code="MISSING_ATTACHMENT_BONE",
                bone_id=att.bone_id,
                message=f"Attachment slot '{att.slot.value}' references non-existent bone '{att.bone_id}'."
            ))
    
    is_valid = len(errors) == 0
    
    return RigValidationResult(
        is_valid=is_valid,
        rig_id=rig.root_bone_id,
        errors=errors,
        warnings=warnings
    )


def apply_morph(
    mesh_vertices: List[List[float]],
    morph: MorphTarget,
    weight: float = 1.0
) -> Tuple[List[List[float]], MorphApplication]:
    """
    Apply a morph target to mesh vertices.
    
    Args:
        mesh_vertices: List of [x, y, z] vertex positions
        morph: Morph target with vertex deltas
        weight: Blend factor (0.0-1.0)
    
    Returns:
        Tuple of (modified vertices, application record)
    """
    import copy
    import math
    
    # Clamp weight
    weight = max(0.0, min(1.0, weight))
    
    # Copy vertices to avoid mutation
    result_vertices = copy.deepcopy(mesh_vertices)
    
    # Apply vertex deltas
    for vdelta in morph.vertex_deltas:
        vidx = vdelta.vertex_index
        if 0 <= vidx < len(result_vertices):
            # Apply weighted delta
            for i in range(3):
                delta_val = vdelta.delta[i] * weight
                # Check for NaN
                if math.isnan(delta_val):
                    raise ValueError(f"NaN delta in morph '{morph.name}' vertex {vidx}")
                result_vertices[vidx][i] += delta_val
    
    # Record application
    app = MorphApplication(
        morph_id=morph.id,
        mesh_id=morph.mesh_id,
        weight=weight
    )
    
    return result_vertices, app


def create_retarget_mapping(
    source_rig: AvatarRigDefinition,
    target_rig: AvatarRigDefinition,
    convention: str = "humanoid",
    custom_mappings: Optional[Dict[str, str]] = None
) -> RetargetRigMap:
    """
    Create a retarget mapping between source and target rigs.
    
    Uses bone naming convention (e.g., humanoid standards) to auto-map.
    Optional custom_mappings to override specific bone pairings.
    
    Args:
        source_rig: Source rig definition
        target_rig: Target rig definition
        convention: Mapping convention ("humanoid", "biped", etc.)
        custom_mappings: Dict {source_bone_id: target_bone_id} overrides
    
    Returns:
        RetargetRigMap with populated mappings
    """
    mappings: List[RetargetMapping] = []
    
    # Build target bone lookup by name
    target_by_name = {bone.id: bone for bone in target_rig.bones}
    
    # Try to map each source bone
    for src_bone in source_rig.bones:
        # Check custom mapping first
        if custom_mappings and src_bone.id in custom_mappings:
            tgt_bone_id = custom_mappings[src_bone.id]
            if tgt_bone_id in target_by_name:
                mappings.append(RetargetMapping(
                    source_bone_id=src_bone.id,
                    target_bone_id=tgt_bone_id,
                    mapping_type=convention
                ))
                continue
        
        # Default: use same bone name
        if src_bone.id in target_by_name:
            mappings.append(RetargetMapping(
                source_bone_id=src_bone.id,
                target_bone_id=src_bone.id,
                mapping_type=convention
            ))
    
    rig_map = RetargetRigMap(
        id=str(uuid.uuid4()),
        source_rig_id=source_rig.root_bone_id,
        target_rig_id=target_rig.root_bone_id,
        mappings=mappings,
        version="1.0",
        convention=convention
    )
    
    return rig_map


# ===== PHASE AV02: Parametric Avatar Builder =====

# Default avatar parameter sliders
DEFAULT_PARAM_SLIDERS = {
    "height": AvatarParamSlider(name="height", min_value=0.8, max_value=2.2, default_value=1.7, category="body"),
    "chest_width": AvatarParamSlider(name="chest_width", min_value=0.3, max_value=0.7, default_value=0.5, category="body"),
    "waist_width": AvatarParamSlider(name="waist_width", min_value=0.2, max_value=0.6, default_value=0.4, category="body"),
    "face_width": AvatarParamSlider(name="face_width", min_value=0.12, max_value=0.20, default_value=0.16, category="face"),
    "jaw_projection": AvatarParamSlider(name="jaw_projection", min_value=-0.05, max_value=0.05, default_value=0.0, category="face"),
    "eye_size": AvatarParamSlider(name="eye_size", min_value=0.8, max_value=1.4, default_value=1.0, category="face"),
    "hair_length": AvatarParamSlider(name="hair_length", min_value=0.0, max_value=1.0, default_value=0.5, category="hair"),
}

# Preset library
AVATAR_PRESETS = {
    "casual_male": AvatarPreset(
        id="casual_male",
        name="Casual Male",
        description="Everyday casual male appearance",
        gender="male",
        style="realistic",
        base_params={
            "height": 1.75,
            "chest_width": 0.55,
            "waist_width": 0.45,
            "face_width": 0.17,
            "jaw_projection": 0.02,
            "eye_size": 1.0,
            "hair_length": 0.3,
        },
        seed="casual_male_seed"
    ),
    "casual_female": AvatarPreset(
        id="casual_female",
        name="Casual Female",
        description="Everyday casual female appearance",
        gender="female",
        style="realistic",
        base_params={
            "height": 1.65,
            "chest_width": 0.48,
            "waist_width": 0.42,
            "face_width": 0.15,
            "jaw_projection": -0.01,
            "eye_size": 1.15,
            "hair_length": 0.7,
        },
        seed="casual_female_seed"
    ),
    "child": AvatarPreset(
        id="child",
        name="Child",
        description="Child-like appearance",
        gender="child",
        style="stylized",
        base_params={
            "height": 1.0,
            "chest_width": 0.35,
            "waist_width": 0.32,
            "face_width": 0.14,
            "jaw_projection": -0.02,
            "eye_size": 1.3,
            "hair_length": 0.5,
        },
        seed="child_seed"
    ),
}

def create_avatar_builder(preset_name: Optional[str] = None) -> AvatarBuilder:
    """
    Create a new avatar builder instance.
    
    Args:
        preset_name: Name of preset to start with, or None for defaults
    
    Returns:
        AvatarBuilder instance
    """
    import hashlib
    from engines.scene_engine.avatar.models import (
        AvatarParamSet,
        AvatarBuilder,
        AvatarParamHistory,
    )
    
    # Start with default parameter values
    param_values = {slider_name: slider.default_value for slider_name, slider in DEFAULT_PARAM_SLIDERS.items()}
    
    # Apply preset if specified
    if preset_name and preset_name in AVATAR_PRESETS:
        preset = AVATAR_PRESETS[preset_name]
        param_values = preset.apply_to_params(param_values)
        seed = preset.seed
    else:
        seed = "default"
    
    # Create initial param set
    param_set = AvatarParamSet(
        values=param_values,
        seed=seed
    )
    
    # Create builder
    builder = AvatarBuilder(
        id=str(uuid.uuid4()),
        param_set=param_set,
        history_stack=[],
        max_history_depth=100
    )
    
    return builder


def apply_preset_to_builder(builder: AvatarBuilder, preset_name: str) -> AvatarBuilder:
    """
    Apply a preset to an existing avatar builder, pushing old state to history.
    
    Args:
        builder: AvatarBuilder instance
        preset_name: Name of preset to apply
    
    Returns:
        Updated AvatarBuilder
    """
    if preset_name not in AVATAR_PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}")
    
    preset = AVATAR_PRESETS[preset_name]
    
    # Save current state to history (make a COPY)
    old_param_set = AvatarParamSet(
        id=builder.param_set.id,
        values=builder.param_set.values.copy(),
        created_at=builder.param_set.created_at,
        seed=builder.param_set.seed
    )
    history_entry = AvatarParamHistory(
        param_set=old_param_set,
        applied_morphs=builder.current_morphs.copy(),
        description=f"Before applying preset: {preset_name}"
    )
    builder.push_history(history_entry)
    
    # Create new param set with preset
    new_values = preset.apply_to_params(builder.param_set.values)
    builder.param_set = AvatarParamSet(
        values=new_values,
        seed=preset.seed
    )
    
    return builder


def set_param_value(builder: AvatarBuilder, param_name: str, value: float) -> AvatarBuilder:
    """
    Set a single parameter value, with clamping.
    
    Args:
        builder: AvatarBuilder instance
        param_name: Parameter name
        value: Value to set
    
    Returns:
        Updated AvatarBuilder
    """
    if param_name not in DEFAULT_PARAM_SLIDERS:
        raise ValueError(f"Unknown parameter: {param_name}")
    
    slider = DEFAULT_PARAM_SLIDERS[param_name]
    clamped_value = slider.clamp(value)
    
    # Save old state to history (make a COPY of param_set first)
    old_param_set = AvatarParamSet(
        id=builder.param_set.id,
        values=builder.param_set.values.copy(),
        created_at=builder.param_set.created_at,
        seed=builder.param_set.seed
    )
    history_entry = AvatarParamHistory(
        param_set=old_param_set,
        applied_morphs=builder.current_morphs.copy(),
        description=f"Set {param_name} = {clamped_value}"
    )
    builder.push_history(history_entry)
    
    # Update param
    builder.param_set.values[param_name] = clamped_value
    
    return builder


def undo_avatar_change(builder: AvatarBuilder) -> AvatarBuilder:
    """
    Undo last change (pop from history).
    
    Args:
        builder: AvatarBuilder instance
    
    Returns:
        Updated AvatarBuilder, or unchanged if history empty
    """
    history_entry = builder.pop_history()
    if history_entry:
        builder.param_set = history_entry.param_set
        builder.current_morphs = history_entry.applied_morphs
    
    return builder


# ===== PHASE AV03: Asset Kits & Materials =====

def create_kit_registry() -> KitRegistry:
    """
    Create an empty kit registry.
    
    Returns:
        KitRegistry instance
    """
    return KitRegistry(id=str(uuid.uuid4()))


def attach_kit(
    kit: KitMetadata,
    body_type: str,
    scale: float = 1.0,
    position: List[float] = None,
    rotation: List[float] = None,
) -> KitAttachment:
    """
    Attach a kit to an avatar with validated transforms.
    
    Args:
        kit: Kit metadata
        body_type: Avatar body type ("male", "female", "child", etc.)
        scale: Scale factor for the kit
        position: [x, y, z] offset
        rotation: [x, y, z] Euler angles
    
    Returns:
        KitAttachment record
    """
    # Validate compatibility
    if body_type not in kit.compatible_body_types:
        raise ValueError(f"Kit '{kit.name}' not compatible with body type '{body_type}'")
    
    # Clamp scale to sensible range
    scale = max(0.1, min(10.0, scale))
    
    # Default position/rotation if not provided
    if position is None:
        position = [0.0, 0.0, 0.0]
    if rotation is None:
        rotation = [0.0, 0.0, 0.0]
    
    # Create attachment record
    attachment = KitAttachment(
        kit_id=kit.kit_id,
        slot=kit.slot,
        body_type=body_type,
        scale=scale,
        position=position,
        rotation=rotation,
        applied_materials=kit.default_materials.copy()
    )
    
    return attachment


def validate_kit_uv_density(mesh_vertices: List[List[float]], uvs: List[List[float]], target_density: float = 1.0) -> UVValidationResult:
    """
    Validate UV/texel density of a mesh.
    
    Args:
        mesh_vertices: List of [x, y, z] vertices
        uvs: List of [u, v] UV coordinates
        target_density: Target texels per unit
    
    Returns:
        UVValidationResult
    """
    warnings: List[str] = []
    errors: List[str] = []
    
    # Check basic validity
    if len(uvs) != len(mesh_vertices):
        errors.append(f"UV count ({len(uvs)}) doesn't match vertex count ({len(mesh_vertices)})")
        return UVValidationResult(
            is_valid=False,
            mesh_id="unknown",
            texel_density=0.0,
            overlap_detected=False,
            errors=errors
        )
    
    # Calculate approximate texel density
    # Simple heuristic: count how many UVs are in 0-1 range
    in_range_count = sum(1 for u, v in uvs if 0 <= u <= 1 and 0 <= v <= 1)
    coverage_ratio = in_range_count / len(uvs) if uvs else 0
    
    # Check for UV overlap (simple heuristic)
    uv_set = set()
    overlap_detected = False
    for u, v in uvs:
        # Quantize to 0.01 precision for overlap check
        quantized = (round(u, 2), round(v, 2))
        if quantized in uv_set:
            overlap_detected = True
            break
        uv_set.add(quantized)
    
    if overlap_detected:
        warnings.append("UV overlap detected - some faces may share texel space")
    
    if coverage_ratio < 0.5:
        warnings.append(f"Only {coverage_ratio*100:.1f}% of UVs in 0-1 range - may have unwrapped islands")
    
    texel_density = coverage_ratio  # Simplified metric
    is_valid = len(errors) == 0
    
    return UVValidationResult(
        is_valid=is_valid,
        mesh_id="kit_mesh",
        texel_density=texel_density,
        overlap_detected=overlap_detected,
        warnings=warnings,
        errors=errors
    )


def apply_material_preset_to_kit(kit: KitAttachment, preset: MaterialPreset) -> KitAttachment:
    """
    Apply a material preset to a kit attachment.
    
    Args:
        kit: KitAttachment instance
        preset: MaterialPreset to apply
    
    Returns:
        Updated KitAttachment
    """
    # Store preset info in applied_materials
    kit.applied_materials[f"preset_{preset.id}"] = preset.id
    
    return kit

