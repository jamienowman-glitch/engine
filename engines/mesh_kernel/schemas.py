"""Mesh Kernel Schemas (Creative Muscle) v1."""
from __future__ import annotations

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# --- Primitives ---
class Vector3Model(BaseModel):
    x: float
    y: float
    z: float

class MeshObject(BaseModel):
    """
    A lightweight mesh for creative manipulation.
    Trimesh-compatible structure.
    """
    id: str
    vertices: List[List[float]] # [[x,y,z], ...] for NumPy speed
    faces: List[List[int]]      # [[i0,i1,i2], ...]
    
    # Optional Attributes
    vertex_colors: Optional[List[List[float]]] = None # [r,g,b,a]
    uvs: Optional[List[List[float]]] = None # [[u,v], ...]
    
    # Material Assignment
    # Dict mapping MaterialID -> List of Face Indices
    material_groups: Dict[str, List[int]] = Field(default_factory=dict)
    
    # Rigging (Skin Weights)
    # List of maps per vertex: [{"bone_id": weight, ...}, ...]
    # For speed, usually: List[List[int]] (bone_indices) and List[List[float]] (weights)
    # Let's simple V1:
    skin_weights: Optional[List[Dict[str, float]]] = None # List matches vertices
    
    # Metadata
    groups: Dict[str, List[int]] = Field(default_factory=dict) # Group Name -> Face Indices
    tags: List[str] = Field(default_factory=list)
    
    # Subdivision Control
    # Set of sharp edges. Tuple (v1, v2) where v1 < v2.
    # Stored as List[List[int]] for JSON.
    crease_edges: List[List[int]] = Field(default_factory=list)

# --- Atomic Operations (Agent Instruction Set) ---

class SculptBrushType(str, Enum):
    MOVE = "MOVE"       # Grab and pull
    SMOOTH = "SMOOTH"   # Average positions
    INFLATE = "INFLATE" # Push along normal
    FLATTEN = "FLATTEN" # Project to plane

class SculptOp(BaseModel):
    """Atomic sculpting stroke."""
    brush: SculptBrushType
    center: Vector3Model
    radius: float
    strength: float
    falloff: float = 0.5 # 0.0=Hard, 1.0=Soft

class SubDOp(BaseModel):
    """Catmull-Clark subdivision."""
    iterations: int = 1

class MeshBooleanType(str, Enum):
    UNION = "UNION"
    DIFFERENCE = "DIFFERENCE"
    INTERSECTION = "INTERSECTION"

class MeshBooleanOp(BaseModel):
    """Approximate boolean for meshes."""
    kind: MeshBooleanType
    target_mesh_id: str
    tool_mesh_id: str

class AgentMeshInstruction(BaseModel):
    """
    The atomic token sent by a 'Creative Agent' to drive this kernel.
    """
    op_code: str # SCULPT, SUBDIVIDE, BOOLEAN, PRIMITIVE
    params: Dict[str, Any]
    target_id: Optional[str] = None
