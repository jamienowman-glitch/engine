"""Tests for glTF Import Engine."""
import json
import base64
import struct
import pytest
from engines.scene_engine.io.gltf_import import (
    gltf_bytes_to_scene_v2,
    GltfImportOptions,
)

def create_triangle_gltf_json() -> bytes:
    """Creates a minimal valid glTF JSON with one triangle (embedded buffer)."""
    # 1. Geometry Data (float32, 3 floats per vert, 3 verts)
    # 0,0,0; 1,0,0; 0,1,0
    positions = [
        0.0, 0.0, 0.0,
        1.0, 0.0, 0.0,
        0.0, 1.0, 0.0
    ]
    pos_bytes = struct.pack('<' + 'f'*9, *positions)
    
    # Indices (unsigned short, 3 indices)
    # 0, 1, 2
    indices = [0, 1, 2]
    idx_bytes = struct.pack('<' + 'H'*3, *indices)
    
    # Concatenate
    buffer_data = pos_bytes + idx_bytes
    b64_data = base64.b64encode(buffer_data).decode('utf-8')
    data_uri = f"data:application/octet-stream;base64,{b64_data}"
    
    # Offsets
    pos_len = len(pos_bytes)
    idx_len = len(idx_bytes)
    
    gltf = {
        "asset": {"version": "2.0"},
        "buffers": [{
            "uri": data_uri,
            "byteLength": len(buffer_data)
        }],
        "bufferViews": [
            {
                "buffer": 0,
                "byteOffset": 0,
                "byteLength": pos_len,
                "target": 34962 # ARRAY_BUFFER
            },
            {
                "buffer": 0,
                "byteOffset": pos_len,
                "byteLength": idx_len,
                "target": 34963 # ELEMENT_ARRAY_BUFFER
            }
        ],
        "accessors": [
            {
                "bufferView": 0,
                "byteOffset": 0,
                "componentType": 5126, # FLOAT
                "count": 3,
                "type": "VEC3",
                "max": [1.0, 1.0, 0.0],
                "min": [0.0, 0.0, 0.0]
            },
            {
                "bufferView": 1,
                "byteOffset": 0,
                "componentType": 5123, # UNSIGNED_SHORT
                "count": 3,
                "type": "SCALAR"
            }
        ],
        "meshes": [
            {
                "primitives": [{
                    "attributes": {"POSITION": 0},
                    "indices": 1
                }]
            }
        ],
        "nodes": [
            {"name": "TriangleNode", "mesh": 0}
        ],
        "scene": 0,
        "scenes": [{"nodes": [0]}]
    }
    return json.dumps(gltf).encode('utf-8')


def test_gltf_import_single_triangle():
    data = create_triangle_gltf_json()
    scene = gltf_bytes_to_scene_v2(data)
    
    # Verify Structure
    assert len(scene.nodes) == 1
    assert scene.nodes[0].name == "TriangleNode"
    assert scene.nodes[0].mesh_id is not None
    
    # Verify Mesh
    assert len(scene.meshes) == 1
    mesh = scene.meshes[0]
    assert len(mesh.vertices) == 3
    assert len(mesh.indices) == 3
    
    # Check Vertex Content
    v0 = mesh.vertices[0]
    assert v0.x == 0 and v0.y == 0
    v1 = mesh.vertices[1]
    assert v1.x == 1.0


def test_gltf_import_materials():
    gltf = {
        "asset": {"version": "2.0"},
        "materials": [
            {
                "name": "RedMetal",
                "pbrMetallicRoughness": {
                    "baseColorFactor": [1.0, 0.0, 0.0, 1.0],
                    "metallicFactor": 0.8,
                    "roughnessFactor": 0.2
                }
            }
        ]
    }
    data = json.dumps(gltf).encode('utf-8')
    scene = gltf_bytes_to_scene_v2(data)
    
    assert len(scene.materials) == 1
    mat = scene.materials[0]
    assert mat.name == "RedMetal"
    assert mat.base_color.x == 1.0
    assert mat.metallic == 0.8


def test_gltf_import_hierarchy():
    gltf = {
        "asset": {"version": "2.0"},
        "nodes": [
            {"name": "Root", "children": [1]},
            {"name": "Child", "translation": [0, 5, 0]}
        ],
        "scene": 0,
        "scenes": [{"nodes": [0]}]
    }
    data = json.dumps(gltf).encode('utf-8')
    scene = gltf_bytes_to_scene_v2(data)
    
    assert len(scene.nodes) == 1 # Only root is top-level
    root = scene.nodes[0]
    assert root.name == "Root"
    assert len(root.children) == 1
    child = root.children[0]
    assert child.name == "Child"
    assert child.transform.position.y == 5.0
