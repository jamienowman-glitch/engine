"""GLTF Import Engine for SceneV2."""
from __future__ import annotations

import json
import struct
import base64
import math
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum

from pydantic import BaseModel

from engines.scene_engine.core.geometry import (
    Material,
    Mesh,
    PrimitiveKind,
    PrimitiveParams,
    Transform,
    Vector3,
    UV, # Was Vector2
    Quaternion,
    EulerAngles,
)
from engines.scene_engine.core.scene_v2 import (
    SceneV2,
    SceneNodeV2,
    ConstructionOp,
    ConstructionOpKind,
)
from engines.scene_engine.core.types import Camera


class GltfImportOptions(BaseModel):
    merge_nodes: bool = False
    generate_missing_normals: bool = True
    center_scene: bool = True
    scale: float = 1.0


# --- Constants ---
GLB_MAGIC = 0x46546C67
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942


class GltfComponentType(int, Enum):
    BYTE = 5120
    UNSIGNED_BYTE = 5121
    SHORT = 5122
    UNSIGNED_SHORT = 5123
    UNSIGNED_INT = 5125
    FLOAT = 5126

# Size in bytes
COMPONENT_SIZE = {
    5120: 1, 5121: 1,
    5122: 2, 5123: 2,
    5125: 4, 5126: 4
}


class MinimalGltfParser:
    """Minimal GLTF/GLB Parser for in-memory bytes."""
    
    def __init__(self, data: bytes):
        self.data = data
        self.json_data: Dict[str, Any] = {}
        self.buffers: List[bytes] = []
        self._parse()

    def _parse(self):
        if self.data[0:4] == b'glTF':
            # Binary GLB
            self._parse_glb()
        else:
            # plain JSON (assuming UTF-8)
            try:
                self.json_data = json.loads(self.data.decode("utf-8"))
            except Exception:
                 # maybe bytes?
                 raise ValueError("Could not parse GLTF JSON")
                 
            # Parse Buffers immediately (P0 supports Data URIs)
            self.buffers = []
            for b_def in self.json_data.get("buffers", []):
                uri = b_def.get("uri")
                if uri and uri.startswith("data:"):
                    self.buffers.append(self._decode_data_uri(uri))
                else:
                    # Placeholder for external file (unsupported) or GLB buffer (shouldn't happen in pure JSON)
                    self.buffers.append(b"")

    def _parse_glb(self):
        magic, version, length = struct.unpack('<III', self.data[0:12])
        if version != 2:
            raise ValueError(f"Unsupported GLTF version: {version}")
        
        offset = 12
        file_len = len(self.data)
        
        while offset < file_len - 8: # Need at least header
            # Read Chunk Header
            chunk_len, chunk_type = struct.unpack('<II', self.data[offset:offset+8])
            offset += 8
            if offset + chunk_len > file_len:
                raise ValueError("GLB chunk truncated")
                
            chunk_data = self.data[offset:offset+chunk_len]
            offset += chunk_len
            
            if chunk_type == CHUNK_JSON:
                self.json_data = json.loads(chunk_data.decode("utf-8"))
            elif chunk_type == CHUNK_BIN:
                # Store binary buffer. 
                # Note: GLB usually has one binary buffer which is refined by BufferViews.
                # However, json['buffers'][0] usually refers to this binary chunk (if undefined uri).
                # We can store it in a list.
                if not self.buffers:
                    self.buffers.append(chunk_data)
                else: 
                    # multiple binary chunks? Rare in standard GLB but possible extensions.
                    self.buffers.append(chunk_data)

    def get_buffer_view_data(self, buffer_view_index: int) -> bytes:
        views = self.json_data.get("bufferViews", [])
        if buffer_view_index >= len(views):
             raise ValueError(f"Invalid bufferView index {buffer_view_index}")
             
        view = views[buffer_view_index]
        buffer_idx = view.get("buffer", 0)
        byte_offset = view.get("byteOffset", 0)
        byte_length = view.get("byteLength", 0)
        
        if buffer_idx >= len(self.buffers):
             raise ValueError(f"Buffer {buffer_idx} missing")
             
        buf_data = self.buffers[buffer_idx]
        if not buf_data:
             # Check if it was supposed to be external?
             # For P0, empty means failed to load (or unsupported external ref)
             raise ValueError(f"Buffer {buffer_idx} data is empty (unsupported URI?)")
             
        return buf_data[byte_offset : byte_offset + byte_length]

    def _decode_data_uri(self, uri: str) -> bytes:
        header, encoded = uri.split(",", 1)
        if "base64" in header:
            return base64.b64decode(encoded)
        raise ValueError("Only base64 data URIs supported")

    def read_accessor(self, accessor_idx: int) -> List[Any]:
        """Reads accessor data and returns list of values (tuples for vectors)."""
        accessors = self.json_data.get("accessors", [])
        acc = accessors[accessor_idx]
        
        buffer_view_idx = acc.get("bufferView")
        if buffer_view_idx is None:
             # Sparse accessor or initialization with zeros? P0: unsupported/zeros
             count = acc.get("count", 0)
             type_str = acc.get("type", "SCALAR")
             # Return zeros
             return self._zeros(count, type_str)

        bv_data = self.get_buffer_view_data(buffer_view_idx)
        
        byte_offset = acc.get("byteOffset", 0)
        component_type = acc.get("componentType")
        count = acc.get("count")
        type_str = acc.get("type")
        
        comp_size = COMPONENT_SIZE.get(component_type, 1)
        
        # Num components per element
        num_comp = {
            "SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16
        }.get(type_str, 1)
        
        # Default stride = tightly packed
        stride = num_comp * comp_size
        
        # Check if bufferView has byteStride?
        views = self.json_data.get("bufferViews", [])
        view = views[buffer_view_idx]
        if "byteStride" in view:
            stride = view["byteStride"]
            
        # Parse format
        # struct fmt chars: b/B (byte), h/H (short), i/I (int), f (float)
        fmt_char = {
            5120: 'b', 5121: 'B',
            5122: 'h', 5123: 'H',
            5125: 'I', # unsigned Int
            5126: 'f'
        }.get(component_type, 'f')
        
        values = []
        current_offset = byte_offset
        
        # Struct format for one element
        elem_fmt = "<" + (fmt_char * num_comp)
        
        for _ in range(count):
            # Check bounds
            if current_offset + (num_comp * comp_size) > len(bv_data):
                break
                
            elem_data = bv_data[current_offset : current_offset + (num_comp * comp_size)]
            val = struct.unpack(elem_fmt, elem_data)
            if len(val) == 1:
                values.append(val[0])
            else:
                values.append(val)
                
            current_offset += stride
            
        return values

    def _zeros(self, count, type_str):
        num_comp = {"SCALAR": 1, "VEC3": 3}.get(type_str, 1) # simple fallback
        if num_comp == 1: return [0] * count
        return [(0,) * num_comp] * count


# --- Conversion Logic ---

def gltf_bytes_to_scene_v2(data: bytes, options: Optional[GltfImportOptions] = None) -> SceneV2:
    if options is None:
        options = GltfImportOptions()
        
    parser = MinimalGltfParser(data)
    json_root = parser.json_data
    
    scene = SceneV2(
        id="parsed_gltf_scene",
        nodes=[], meshes=[], materials=[],
        camera=None, 
        history=[ConstructionOp(id="gltf_import", kind=ConstructionOpKind.CREATE_PRIMITIVE, params={"source": "gltf"})]
    )
    
    # 1. Materials
    # Map Gltf material index -> Scene Material ID
    mat_map = {}
    if "materials" in json_root:
        for i, mat_def in enumerate(json_root["materials"]):
            mat = _parse_material(mat_def, i)
            mat_map[i] = mat.id
            scene.materials.append(mat)
            
    # 2. Meshes
    # Map Gltf mesh index -> List of Scene Mesh IDs (one per primitive)
    mesh_primitive_map: Dict[int, List[str]] = {} # index -> [mesh_id_p1, mesh_id_p2]
    
    if "meshes" in json_root:
        for i, mesh_def in enumerate(json_root["meshes"]):
            primitives = mesh_def.get("primitives", [])
            created_ids = []
            for j, prim in enumerate(primitives):
                mesh_obj = _parse_primitive(parser, prim, i, j, mat_map)
                scene.meshes.append(mesh_obj)
                created_ids.append(mesh_obj.id)
            mesh_primitive_map[i] = created_ids
            
    # 3. Nodes
    nodes_flat = []
    if "nodes" in json_root:
        for i, node_def in enumerate(json_root["nodes"]):
            # Transform
            trans = _parse_transform(node_def)
            
            # Mesh?
            mesh_index = node_def.get("mesh")
            
            # If mesh has multiple primitives, we treat this node as Group, and append children.
            # If mesh has 1 primitive, we attach mesh to this node.
            
            my_mesh_id = None
            extra_children = []
            
            if mesh_index is not None:
                p_ids = mesh_primitive_map.get(mesh_index, [])
                if len(p_ids) == 1:
                    my_mesh_id = p_ids[0]
                elif len(p_ids) > 1:
                    # Create children for each primitive
                    for k, pid in enumerate(p_ids):
                        child = SceneNodeV2(
                            id=f"node_{i}_prim_{k}",
                            name=f"{node_def.get('name', 'Node')}_p{k}",
                            # Identity transform for primitive child
                            transform=Transform(
                                position=Vector3(x=0.0, y=0.0, z=0.0),
                                rotation=EulerAngles(x=0.0, y=0.0, z=0.0), # Default Euler
                                scale=Vector3(x=1.0, y=1.0, z=1.0)
                            ),
                            mesh_id=pid,
                            meta={"source": "gltf_primitive"}
                        )
                        extra_children.append(child)
            
            scene_node = SceneNodeV2(
                id=f"node_{i}",
                name=node_def.get("name", f"Node_{i}"),
                transform=trans,
                mesh_id=my_mesh_id,
                children=extra_children, 
                meta={"source": "gltf", "gltf_index": i}
            )
            nodes_flat.append(scene_node)
            
    # Link hierarchy
    if "nodes" in json_root:
        for i, node_def in enumerate(json_root["nodes"]):
            parent = nodes_flat[i]
            for child_idx in node_def.get("children", []):
                parent.children.append(nodes_flat[child_idx])
                
    # 4. Scene Root
    scene_idx = json_root.get("scene", 0)
    scenes = json_root.get("scenes", [])
    if scenes and scene_idx < len(scenes):
        root_indices = scenes[scene_idx].get("nodes", [])
        for idx in root_indices:
            scene.nodes.append(nodes_flat[idx])
            
    # 5. Post Processing (Center/Scale)
    if options.center_scene or options.scale != 1.0:
        _apply_post_processing(scene, options)
        
    return scene


def _parse_material(mat_def: Dict, index: int) -> Material:
    pbr = mat_def.get("pbrMetallicRoughness", {})
    base_col_factor = pbr.get("baseColorFactor", [1, 1, 1, 1])
    metallic = pbr.get("metallicFactor", 1.0)
    roughness = pbr.get("roughnessFactor", 1.0)
    
    mat = Material(
        id=f"mat_{index}",
        name=mat_def.get("name", f"Material_{index}"),
        base_color=Vector3(x=float(base_col_factor[0]), y=float(base_col_factor[1]), z=float(base_col_factor[2])),
        metallic=float(metallic),
        roughness=float(roughness)
    )
    return mat


def _parse_transform(node_def: Dict) -> Transform:
    # Handle TRS
    t = node_def.get("translation", [0.0, 0.0, 0.0])
    r = node_def.get("rotation", [0.0, 0.0, 0.0, 1.0]) # quaternion xyzw
    s = node_def.get("scale", [1.0, 1.0, 1.0])
    
    return Transform(
        position=Vector3(x=float(t[0]), y=float(t[1]), z=float(t[2])),
        # Use Quaternion directly
        rotation=Quaternion(x=float(r[0]), y=float(r[1]), z=float(r[2]), w=float(r[3])),
        scale=Vector3(x=float(s[0]), y=float(s[1]), z=float(s[2]))
    )


def _parse_primitive(parser: MinimalGltfParser, prim: Dict, mesh_idx: int, prim_idx: int, mat_map: Dict) -> Mesh:
    attrs = prim.get("attributes", {})
    
    # Vertices (POSITION) - Required
    pos_idx = attrs.get("POSITION")
    if pos_idx is None:
        raise ValueError(f"Mesh {mesh_idx} primitive {prim_idx} missing POSITION")
    
    positions = parser.read_accessor(pos_idx) # List of (x,y,z)
    
    # Normals
    normals = []
    norm_idx = attrs.get("NORMAL")
    if norm_idx is not None:
        normals = parser.read_accessor(norm_idx)
    
    # UVs
    uvs = []
    tex_idx = attrs.get("TEXCOORD_0")
    if tex_idx is not None:
        uvs = parser.read_accessor(tex_idx)
        
    # Indices
    indices_idx = prim.get("indices")
    if indices_idx is not None:
        indices = parser.read_accessor(indices_idx)
    else:
        # Non-indexed? Generate sequential
        indices = list(range(len(positions)))
        
    # Build Mesh
    
    verts_v3 = [Vector3(x=p[0], y=p[1], z=p[2]) for p in positions]
    norms_v3 = [Vector3(x=n[0], y=n[1], z=n[2]) for n in normals] if normals else []
    
    # uvs are Vector2 (now UV)
    uvs_obj = [UV(u=u[0], v=u[1]) for u in uvs] if uvs else []
    
    mat_id = mat_map.get(prim.get("material"))
    
    return Mesh(
        id=f"mesh_{mesh_idx}_p{prim_idx}",
        vertices=verts_v3,
        indices=indices,
        normals=norms_v3,
        uvs=uvs_obj,
        material_id=mat_id,
        primitive_source=None # Generic mesh
    )

def _apply_post_processing(scene: SceneV2, options: GltfImportOptions):
    s = options.scale
    if s != 1.0:
        for node in scene.nodes:
            node.transform.scale.x *= s
            node.transform.scale.y *= s
            node.transform.scale.z *= s
