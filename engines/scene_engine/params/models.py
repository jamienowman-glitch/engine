"""Parameter Graph Models."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union, Literal

from pydantic import BaseModel, Field

from engines.scene_engine.core.geometry import Vector3


class ParamType(str, Enum):
    FLOAT = "float"
    VECTOR3 = "vector3"
    BOOLEAN = "boolean"
    STRING = "string"


class ParamNodeKind(str, Enum):
    CONSTANT = "constant"
    ADD = "add"
    MULTIPLY = "multiply"
    REMAP = "remap"
    CLAMP = "clamp"
    VECTOR_COMPOSE = "vector_compose"
    SCRIPT_EXPR = "script_expr"
    # New generator nodes
    RANDOM_FLOAT = "random_float"
    NOISE_1D = "noise_1d"
    GRID_2D = "grid_2d"
    TRANSFORM_POINTS = "transform_points"
    SCATTER_ON_SURFACE = "scatter_on_surface"
    # Basic input node (often just a constant or named input)
    INPUT = "input"


class ParamValue(BaseModel):
    kind: ParamType
    # Store value. For simplicity in P0, store as basic python types.
    value: Union[float, str, bool, Vector3, List[float], List[Vector3], List[Any]]


class ParamNode(BaseModel):
    id: str
    kind: ParamNodeKind
    # Inputs: map of input_slot_name -> node_id (connection)
    inputs: Dict[str, str] = Field(default_factory=dict)
    # Params: static configuration (e.g. constant value, script body)
    params: Dict[str, Any] = Field(default_factory=dict)
    
    meta: Dict[str, Any] = Field(default_factory=dict)


class ParamGraph(BaseModel):
    id: str
    nodes: List[ParamNode] = Field(default_factory=list)
    # Exposed inputs for the graph (e.g. "energy" -> node_id)
    exposed_inputs: Dict[str, str] = Field(default_factory=dict)
    # Exposed outputs (e.g. "pose_strength" -> node_id)
    outputs: Dict[str, str] = Field(default_factory=dict)


# --- Bindings ---

class ParamTargetKind(str, Enum):
    NODE_POSITION_Y = "node_position_y"
    NODE_SCALE_UNIFORM = "node_scale_uniform"
    MATERIAL_COLOR = "material_color"
    CAMERA_DISTANCE = "camera_distance"
    AVATAR_STYLE_FIELD = "avatar_style_field"
    NODE_ROTATION_EULER = "node_rotation_euler"


class ParamBinding(BaseModel):
    id: str
    graph_output_name: str
    target_kind: ParamTargetKind
    
    # Target identifiers
    target_id: str # Node ID, Material ID, or Camera ID
    
    # Configuration
    field_name: Optional[str] = None # For AVATAR_STYLE_FIELD (e.g. "height")
    axis: Optional[str] = None # 'x','y','z' if needed specifically
    
    meta: Dict[str, Any] = Field(default_factory=dict)
