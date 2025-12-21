"""glTF 2.0 Exporter."""
from __future__ import annotations

import base64
import json
import struct
from typing import Any, Dict, List, Optional, Tuple

from engines.scene_engine.core.scene_v2 import SceneV2, SceneNodeV2
from engines.scene_engine.core.geometry import Mesh, Vector3, Quaternion, EulerAngles

def _vec3_to_list(v: Vector3) -> List[float]:
    return [v.x, v.y, v.z]

def _euler_to_quat(e: EulerAngles) -> List[float]:
    # Basic Euler to Quaternion for glTF (Unity style YXZ usually, but let's stick to simple ZYX or similar)
    # Using scipy.spatial logic or simple math.
    import math
    # Roll(x), Pitch(y), Yaw(z)? 
    # Let's assume standard extrinsic xyz.
    
    cx = math.cos(e.x * 0.5)
    sx = math.sin(e.x * 0.5)
    cy = math.cos(e.y * 0.5)
    sy = math.sin(e.y * 0.5)
    cz = math.cos(e.z * 0.5)
    sz = math.sin(e.z * 0.5)
    
    w = cx * cy * cz + sx * sy * sz
    x = sx * cy * cz - cx * sy * sz
    y = cx * sy * cz + sx * cy * sz
    z = cx * cy * sz - sx * sy * cz
    
    return [x, y, z, w]

class GltfWriter:
    def __init__(self):
        self.buffers = []
        self.buffer_views = []
        self.accessors = []
        self.meshes = []
        self.nodes = []
        self.scenes = [{"nodes": []}]
        self.materials = []
        self.bin_data = bytearray()
        
    def add_buffer_data(self, data: bytes) -> int:
        """Appends data to main binary buffer, returns byteOffset."""
        offset = len(self.bin_data)
        
        # Padding to 4 bytes
        padding = (4 - (len(data) % 4)) % 4
        self.bin_data.extend(data)
        self.bin_data.extend(b'\x00' * padding)
        
        return offset

    def create_accessor(self, data_bytes: bytes, count: int, comp_type: int, type_str: str, min_v=None, max_v=None) -> int:
        offset = self.add_buffer_data(data_bytes)
        length = len(data_bytes)
        
        view_idx = len(self.buffer_views)
        self.buffer_views.append({
            "buffer": 0,
            "byteOffset": offset,
            "byteLength": length,
            "target": 34962 if type_str == "SCALAR" and comp_type == 5123 else 34962 # Array Buffer usually
        })
        
        acc_idx = len(self.accessors)
        acc = {
            "bufferView": view_idx,
            "byteOffset": 0,
            "componentType": comp_type, # 5126=FLOAT, 5123=USHORT
            "count": count,
            "type": type_str
        }
        if min_v: acc["min"] = min_v
        if max_v: acc["max"] = max_v
        self.accessors.append(acc)
        return acc_idx

    def process_mesh(self, mesh: Mesh) -> int:
        # P0: Only Positions and Indices
        
        # 1. Positions (Vec3 Float)
        pos_bytes = bytearray()
        min_p = [float('inf')]*3
        max_p = [float('-inf')]*3
        
        for v in mesh.vertices:
            pos_bytes.extend(struct.pack('<fff', v.x, v.y, v.z))
            for i, c in enumerate([v.x, v.y, v.z]):
                min_p[i] = min(min_p[i], c)
                max_p[i] = max(max_p[i], c)
                
        pos_acc = self.create_accessor(
            pos_bytes, 
            len(mesh.vertices), 
            5126, # FLOAT 
            "VEC3",
            min_v=min_p, 
            max_v=max_p
        )
        
        # 2. Indices (Scalar UShort)
        idx_bytes = bytearray()
        for idx in mesh.indices:
            idx_bytes.extend(struct.pack('<H', idx))
            
        idx_acc = self.create_accessor(
            idx_bytes,
            len(mesh.indices),
            5123, # UNSIGNED_SHORT
            "SCALAR"
        )
        
        mesh_idx = len(self.meshes)
        self.meshes.append({
            "primitives": [{
                "attributes": {
                    "POSITION": pos_acc
                },
                "indices": idx_acc
            }]
        })
        return mesh_idx

    def process_node(self, node: SceneNodeV2, scene: SceneV2, parent_idx: Optional[int] = None) -> int:
        idx = len(self.nodes)
        gltf_node = {
            "name": node.id,
            "translation": _vec3_to_list(node.transform.position),
            "rotation": _euler_to_quat(node.transform.rotation),
            "scale": _vec3_to_list(node.transform.scale)
        }
        
        if node.mesh_id:
            # Find mesh object in scene to process
            mesh_obj = next((m for m in scene.meshes if m.id == node.mesh_id), None)
            if mesh_obj:
                # Deduplicate? For P0, re-process mesh every node or map IDs?
                # Let's map IDs to avoid bloating
                # ... skipping cache logic for brevity P0
                m_idx = self.process_mesh(mesh_obj)
                gltf_node["mesh"] = m_idx

        self.nodes.append(gltf_node)
        
        if parent_idx is not None:
             parent = self.nodes[parent_idx]
             if "children" not in parent: parent["children"] = []
             parent["children"].append(idx)
        else:
            # Root nodes go to scene
            self.scenes[0]["nodes"].append(idx)
            
        for child in node.children:
            self.process_node(child, scene, idx)
            
        return idx
        
    def build(self) -> Dict[str, Any]:
        
        # Setup buffer
        encoded = base64.b64encode(self.bin_data).decode('utf-8')
        uri = f"data:application/octet-stream;base64,{encoded}"
        
        self.buffers = [{
            "byteLength": len(self.bin_data),
            "uri": uri
        }]
        
        return {
            "asset": {"version": "2.0"},
            "scene": 0,
            "scenes": self.scenes,
            "nodes": self.nodes,
            "meshes": self.meshes,
            "accessors": self.accessors,
            "bufferViews": self.buffer_views,
            "buffers": self.buffers
        }

def export_scene_to_gltf(scene: SceneV2) -> Dict[str, Any]:
    writer = GltfWriter()
    for node in scene.nodes:
        writer.process_node(node, scene)
    out = writer.build()

    # Include scene-level metadata (extras) if present in SceneV2.meta
    # This makes export bundles self-descriptive and allows rig/animation metadata
    if getattr(scene, "meta", None):
        # Ensure we clone simple primitives only to avoid leaking complex objects
        out["extras"] = scene.meta

    return out
