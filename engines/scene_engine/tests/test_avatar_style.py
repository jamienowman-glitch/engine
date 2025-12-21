"""Tests for Avatar Style Parameter Engine."""
from typing import Tuple

from engines.scene_engine.avatar.models import (
    AvatarAttachmentBinding,
    AvatarBodyPart,
    AvatarBone,
    AvatarRigDefinition,
)
from engines.scene_engine.avatar.style import (
    AvatarStyleParams,
    BodyBuild,
    HeadProportion,
    apply_avatar_style,
    extract_avatar_style,
)
from engines.scene_engine.core.geometry import Quaternion, Transform, Vector3

from engines.scene_engine.core.scene_v2 import Material, SceneNodeV2, SceneV2

from engines.scene_engine.core.types import Camera


def _create_test_avatar() -> Tuple[SceneV2, AvatarRigDefinition]:
    """Helper to create a minimal rigged avatar scene."""
    # Nodes
    root = SceneNodeV2(
        id="root_node",
        name="AvatarRoot",
        transform=Transform(
            position=Vector3(x=0, y=0, z=0),
            rotation=Quaternion(x=0, y=0, z=0, w=1),
            scale=Vector3(x=1, y=1, z=1)
        ),
    )
    
    head = SceneNodeV2(
        id="head_node",
        name="Head",
        transform=Transform(
            position=Vector3(x=0, y=1.7, z=0),
            rotation=Quaternion(x=0, y=0, z=0, w=1),
            scale=Vector3(x=1, y=1, z=1)
        ),
        children=[],
        mesh_id="mesh_head"
    )
    
    torso = SceneNodeV2(
        id="torso_node",
        name="Torso",
        transform=Transform(
            position=Vector3(x=0, y=1.0, z=0),
            rotation=Quaternion(x=0, y=0, z=0, w=1),
            scale=Vector3(x=1, y=1, z=1)
        ),
        children=[head],
        mesh_id="mesh_torso"
    )
    
    root.children.append(torso)
    
    nodes = [root]
    
    # Materials
    mat1 = Material(
        id="mat_body",
        name="BodyMat",
        base_color=Vector3(x=0.5, y=0.5, z=0.5)
    )
    
    scene = SceneV2(
        id="scene_1",
        nodes=nodes,
        materials=[mat1],
        meshes=[],
        # camera=None
    )
    
    # Rig
    bones = [
        AvatarBone(id="b_root", part=AvatarBodyPart.PELVIS, node_id="root_node"),
        AvatarBone(id="b_torso", part=AvatarBodyPart.TORSO, node_id="torso_node", parent_id="b_root"),
        AvatarBone(id="b_head", part=AvatarBodyPart.HEAD, node_id="head_node", parent_id="b_torso"),
    ]
    
    rig = AvatarRigDefinition(
        bones=bones,
        attachments=[],
        root_bone_id="b_root"
    )
    
    return scene, rig


def test_apply_style_height_scaling():
    scene, rig = _create_test_avatar()
    
    # Target 2x height (1.8 -> 3.6)
    style = AvatarStyleParams(height=3.6)
    
    new_scene = apply_avatar_style(scene, rig, style)
    
    # Check root scale
    new_root = new_scene.nodes[0]
    # base 1.8. target 3.6. scale should be 2.0
    assert abs(new_root.transform.scale.y - 2.0) < 0.01
    
    # Original should be untouched
    assert scene.nodes[0].transform.scale.y == 1.0


def test_apply_style_proportions():
    scene, rig = _create_test_avatar()
    
    # Slim build -> thinner limbs/torso
    style = AvatarStyleParams(body_build=BodyBuild.SLIM)
    new_scene = apply_avatar_style(scene, rig, style)
    
    # Find torso node
    def find_node(nodes, name):
        for n in nodes:
            if n.name == name: return n
            res = find_node(n.children, name)
            if res: return res
    
    new_torso = find_node(new_scene.nodes, "Torso")
    # Slim torso scale should be < 1.0 (impl assumes 0.9)
    assert new_torso.transform.scale.x < 1.0
    assert new_torso.transform.scale.z < 1.0


def test_apply_style_materials():
    scene, rig = _create_test_avatar()
    
    style = AvatarStyleParams(
        base_color="#FF0000",
        metallic=0.9,
        roughness=0.1
    )
    
    new_scene = apply_avatar_style(scene, rig, style)
    
    # Check material
    mat = new_scene.materials[0]
    assert mat.metallic == 0.9
    assert mat.roughness == 0.1
    assert mat.meta["base_color_override"] == "#FF0000"


def test_extract_returns_stamped_params():
    scene, rig = _create_test_avatar()
    style = AvatarStyleParams(height=2.5, head_proportion=HeadProportion.LARGE)
    
    # Apply stamps it
    applied_scene = apply_avatar_style(scene, rig, style)
    
    # Extract should read it back
    extracted = extract_avatar_style(applied_scene, rig)
    
    assert extracted.height == 2.5
    assert extracted.head_proportion == HeadProportion.LARGE
