
import pytest
import struct
import base64
import json
from engines.scene_engine.core.geometry import Vector3, Mesh, Transform, EulerAngles
from engines.scene_engine.core.scene_v2 import SceneV2, SceneNodeV2
from engines.scene_engine.export.gltf_export import export_scene_to_gltf

def test_gltf_export_structure():
    # Scene with 1 Mesh Node
    
    # Mesh
    mesh = Mesh(
        id="m1",
        vertices=[Vector3(x=0,y=0,z=0), Vector3(x=1,y=0,z=0), Vector3(x=0,y=1,z=0)],
        indices=[0, 1, 2]
    )
    
    node = SceneNodeV2(
        id="n1",
        mesh_id="m1",
        transform=Transform(
            position=Vector3(x=10,y=0,z=0),
            rotation=EulerAngles(x=0,y=0,z=0),
            scale=Vector3(x=1,y=1,z=1)
        )
    )
    
    scene = SceneV2(
        id="s1",
        nodes=[node],
        meshes=[mesh]
    )
    
    gltf = export_scene_to_gltf(scene)
    
    # Verify Top Level
    assert gltf["asset"]["version"] == "2.0"
    assert len(gltf["nodes"]) == 1
    assert gltf["nodes"][0]["name"] == "n1"
    assert gltf["nodes"][0]["translation"] == [10, 0, 0]
    
    # Verify Mesh
    assert len(gltf["meshes"]) == 1
    assert "primitives" in gltf["meshes"][0]
    
    # Verify Buffer
    assert len(gltf["buffers"]) == 1
    uri = gltf["buffers"][0]["uri"]
    assert uri.startswith("data:application/octet-stream;base64,")
    
    # Decode and check length
    b64_data = uri.split(",")[1]
    data = base64.b64decode(b64_data)
    assert len(data) == gltf["buffers"][0]["byteLength"]
