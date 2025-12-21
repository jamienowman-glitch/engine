
import pytest
from engines.scene_engine.core.geometry import Vector3, Transform, EulerAngles
from engines.scene_engine.core.scene_v2 import SceneV2, SceneNodeV2
from engines.scene_engine.extras.lod import LODGroup, LODLevel, apply_lod
from engines.scene_engine.extras.scripting import ScriptRegistry
from engines.scene_engine.extras.instancing import create_instance

def test_lod_switching():
    # Setup Node with LoD
    # mesh_high (dist < 10), mesh_low (dist < 100)
    
    node = SceneNodeV2(
        id="n1",
        mesh_id="mesh_high",
        transform=Transform(
            position=Vector3(x=0,y=0,z=0),
            rotation=EulerAngles(x=0,y=0,z=0),
            scale=Vector3(x=1,y=1,z=1)
        )
    )
    
    scene = SceneV2(id="s1", nodes=[node])
    
    lods = {
        "n1": LODGroup(levels=[
            LODLevel(max_distance=10.0, mesh_id="mesh_high"),
            LODLevel(max_distance=50.0, mesh_id="mesh_low")
        ])
    }
    
    # 1. Camera at 0,0,5 (Dist 5) -> High
    apply_lod(scene, Vector3(x=0,y=0,z=5), lods)
    assert scene.nodes[0].mesh_id == "mesh_high"
    
    # 2. Camera at 0,0,20 (Dist 20) -> Low
    apply_lod(scene, Vector3(x=0,y=0,z=20), lods)
    assert scene.nodes[0].mesh_id == "mesh_low"
    
    # 3. Camera at 0,0,100 (Dist 100) -> Exceeds 50 -> Defaults to last (Low)
    apply_lod(scene, Vector3(x=0,y=0,z=100), lods)
    assert scene.nodes[0].mesh_id == "mesh_low"

def test_script_hooks():
    # Register script
    def move_up(scene: SceneV2) -> SceneV2:
        for n in scene.nodes:
            n.transform.position.y += 10.0
        return scene
        
    ScriptRegistry.register("move_up", move_up)
    
    scene = SceneV2(id="s1", nodes=[SceneNodeV2(id="n1", transform=Transform(position=Vector3(x=0,y=0,z=0), rotation=EulerAngles(x=0,y=0,z=0), scale=Vector3(x=1,y=1,z=1)))])
    
    # Run
    scene = ScriptRegistry.run("move_up", scene)
    assert scene.nodes[0].transform.position.y == 10.0
    
    # Clear
    ScriptRegistry.clear()

def test_instancing():
    proto = SceneNodeV2(
        id="proto1",
        mesh_id="m_proto",
        material_id="mat_proto",
        transform=Transform(position=Vector3(x=0,y=0,z=0), rotation=EulerAngles(x=0,y=0,z=0), scale=Vector3(x=1,y=1,z=1))
    )
    scene = SceneV2(id="s1", nodes=[proto])
    
    # Create instance
    new_id = create_instance(scene, "proto1", Vector3(x=10,y=0,z=0))
    
    # Check
    inst = next(n for n in scene.nodes if n.id == new_id)
    assert inst.mesh_id == "m_proto"
    assert inst.material_id == "mat_proto"
    assert inst.transform.position.x == 10.0
