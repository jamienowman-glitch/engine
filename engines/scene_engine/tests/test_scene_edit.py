"""Tests for Scene Edit Engine (Level B)."""
from engines.scene_engine.core.geometry import (
    BoxParams,
    EulerAngles,
    PrimitiveKind,
    Transform,
    Vector3,
)
from engines.scene_engine.core.scene_v2 import AttachmentPoint
from engines.scene_engine.edit.models import (
    AddPrimitiveNodeCommand,
    CreateSceneCommand,
    DeleteNodeCommand,
    SetNodeAttachmentsCommand,
    UpdateNodeMetaCommand,
    UpdateNodeTransformCommand,
)
from engines.scene_engine.edit.service import (
    add_primitive_node,
    create_scene,
    delete_node,
    set_node_attachments,
    update_node_meta,
    update_node_transform,
)


def test_create_scene_empty():
    cmd = CreateSceneCommand(name="Test Scene", meta={"author": "Max"})
    res = create_scene(cmd)
    
    assert res.scene.id is not None
    assert len(res.scene.nodes) == 0
    assert res.scene.environment["meta"]["name"] == "Test Scene"
    assert res.scene.environment["meta"]["author"] == "Max"


def test_add_primitive_node():
    # Setup
    scene = create_scene(CreateSceneCommand()).scene
    
    # Add Box
    transform = Transform(
        position=Vector3(x=0, y=0, z=0),
        rotation=EulerAngles(x=0, y=0, z=0),
        scale=Vector3(x=1, y=1, z=1)
    )
    box = BoxParams(width=1, height=1, depth=1)
    
    cmd = AddPrimitiveNodeCommand(
        scene=scene,
        primitive=box,
        transform=transform,
        meta={"tag": "box1"}
    )
    
    res = add_primitive_node(cmd)
    
    assert res.node_id is not None
    assert len(res.scene.nodes) == 1
    assert len(res.scene.meshes) == 1
    assert res.scene.nodes[0].id == res.node_id
    assert res.scene.nodes[0].meta["tag"] == "box1"
    
    # Check history
    assert len(res.scene.history) == 1
    assert res.scene.history[0].kind == "CREATE_PRIMITIVE"
    assert res.scene.history[0].result_node_id == res.node_id


def test_update_node_transform():
    # Setup
    scene = create_scene(CreateSceneCommand()).scene
    box = BoxParams(width=1, height=1, depth=1)
    t_start = Transform(
        position=Vector3(x=0, y=0, z=0),
        rotation=EulerAngles(x=0, y=0, z=0),
        scale=Vector3(x=1, y=1, z=1)
    )
    res_add = add_primitive_node(AddPrimitiveNodeCommand(
        scene=scene, primitive=box, transform=t_start
    ))
    
    node_id = res_add.node_id
    scene = res_add.scene
    
    # Update
    t_new = Transform(
        position=Vector3(x=10, y=10, z=10),
        rotation=EulerAngles(x=0, y=45, z=0),
        scale=Vector3(x=2, y=2, z=2)
    )
    
    res_update = update_node_transform(UpdateNodeTransformCommand(
        scene=scene, node_id=node_id, transform=t_new
    ))
    
    updated_node = res_update.scene.nodes[0]
    assert updated_node.transform.position.x == 10.0
    
    # History check
    assert len(res_update.scene.history) == 2 # 1 create + 1 transform


def test_set_node_attachments():
    scene = create_scene(CreateSceneCommand()).scene
    box = BoxParams(width=1, height=1, depth=1)
    t = Transform(
        position=Vector3(x=0, y=0, z=0),
        rotation=EulerAngles(x=0, y=0, z=0),
        scale=Vector3(x=1, y=1, z=1)
    )
    res_add = add_primitive_node(AddPrimitiveNodeCommand(
        scene=scene, primitive=box, transform=t
    ))
    scene = res_add.scene
    node_id = res_add.node_id
    
    # Attach
    att = AttachmentPoint(
        name="socket_top",
        local_transform=Transform(
            position=Vector3(x=0, y=0.5, z=0),
            rotation=EulerAngles(x=0, y=0, z=0),
            scale=Vector3(x=1, y=1, z=1)
        )
    )
    
    res_att = set_node_attachments(SetNodeAttachmentsCommand(
        scene=scene, node_id=node_id, attachments=[att]
    ))
    
    updated_node = res_att.scene.nodes[0]
    assert len(updated_node.attachments) == 1
    assert updated_node.attachments[0].name == "socket_top"


def test_delete_node():
    # Setup: Root -> Child
    scene = create_scene(CreateSceneCommand()).scene
    box = BoxParams(width=1, height=1, depth=1)
    t = Transform(
        position=Vector3(x=0, y=0, z=0),
        rotation=EulerAngles(x=0, y=0, z=0),
        scale=Vector3(x=1, y=1, z=1)
    )
    
    # Create Root
    res_root = add_primitive_node(AddPrimitiveNodeCommand(
        scene=scene, primitive=box, transform=t
    ))
    root_id = res_root.node_id
    scene = res_root.scene
    
    # Create Child
    res_child = add_primitive_node(AddPrimitiveNodeCommand(
        scene=scene, primitive=box, transform=t, parent_node_id=root_id
    ))
    child_id = res_child.node_id
    scene = res_child.scene
    
    # Verify hierarchy
    assert len(scene.nodes) == 1  # Logic adds root to nodes list
    assert len(scene.nodes[0].children) == 1
    assert scene.nodes[0].children[0].id == child_id
    
    # Delete Root
    res_del = delete_node(DeleteNodeCommand(scene=scene, node_id=root_id))
    
    # Verify gone
    assert len(res_del.scene.nodes) == 0
