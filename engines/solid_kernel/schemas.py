"""Solid Kernel Schemas (Precision Muscle) v1."""
from __future__ import annotations

from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field

# --- Primitives ---

class Point3(BaseModel):
    x: float
    y: float
    z: float

# --- Solid Object (CAD Wrapper) ---

class SolidObject(BaseModel):
    """
    A placeholder for a robust BREP solid.
    In V1, this mainly holds the History/Recipe since the actual kernel (OCCT/Manifold)
    holds the heavy memory pointer.
    """
    id: str
    kernel_ref_id: str # Pointer to C++ memory or temp file path (STEP/GLB)
    
    # Construction History (Parametric)
    history: List[AgentSolidInstruction] = Field(default_factory=list)
    
    # Metadata
    mass: Optional[float] = None
    volume: Optional[float] = None
    center_of_mass: Optional[Point3] = None

# --- Atomic Operations (Agent Instruction Set) ---

class SolidPrimitiveType(str, Enum):
    BOX = "BOX"
    CYLINDER = "CYLINDER"
    SPHERE = "SPHERE"
    CONE = "CONE"

class ExtrudeOp(BaseModel):
    """Extrude a 2D profile (Sketch) into 3D."""
    sketch_id: str # Ref to a generic Sketch from scene_engine?
    distance: float
    direction: Point3 = Point3(x=0,y=0,z=1)

class FilletOp(BaseModel):
    """Round off specific edges."""
    edge_indices: List[int] # Needs stable ID logic from kernel
    radius: float

class SolidBooleanType(str, Enum):
    UNION = "UNION"
    DIFFERENCE = "DIFFERENCE"
    INTERSECTION = "INTERSECTION"

class SolidBooleanOp(BaseModel):
    """Exact boolean for solids."""
    kind: SolidBooleanType
    target_id: str # The main body
    tool_id: str   # The tool body (consumed?)

class AgentSolidInstruction(BaseModel):
    """
    The atomic token sent by a 'Precision Agent' to drive this kernel.
    """
    op_code: str # PRIMITIVE, EXTRUDE, FILLET, BOOLEAN
    params: Dict[str, Any]
    target_id: Optional[str] = None
