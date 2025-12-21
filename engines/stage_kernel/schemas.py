"""Stage Engine Schemas (The Stage)."""
from __future__ import annotations
from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

# We reuse Scene Engine types where possible to avoid duplication
from engines.scene_engine.core.geometry import Vector3

class PropType(str, Enum):
    STATIC_MESH = "STATIC_MESH"
    EMITTER = "EMITTER"
    CAMERA = "CAMERA"

class PropDefinition(BaseModel):
    """A template for a potentially spawnable item."""
    id: str
    name: str
    kind: PropType
    mesh_asset_id: Optional[str] = None # Ref to a Mesh in the Library
    default_scale: Vector3 = Vector3(x=1,y=1,z=1)
    tags: List[str] = Field(default_factory=list)

class StageLightType(str, Enum):
    SUN = "SUN"
    POINT = "POINT"
    SPOT = "SPOT"
    AMBIENT = "AMBIENT"

class StageOpCode(str, Enum):
    SPAWN_PROP = "SPAWN_PROP"
    SET_LIGHT = "SET_LIGHT"
    SET_ENV = "SET_ENV" # e.g. Skybox

class AgentStageInstruction(BaseModel):
    """Atomic token for the Stage Engine."""
    op_code: str # SPAWN_PROP, SET_LIGHT
    params: Dict[str, Any]
    target_scene_id: Optional[str] = None
