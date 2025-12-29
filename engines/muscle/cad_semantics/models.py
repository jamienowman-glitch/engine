"""
CAD Semantics Models - Semantic classification and spatial graph structures.

Defines:
- SemanticType: Wall, Door, Window, Slab, Column, Room, Level
- SemanticElement: Classified CAD element with type, attributes, level
- SpatialGraphEdge: Adjacency, containment, connectivity
- SpatialGraph: Complete semantic topology
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class SemanticType(str, Enum):
    """Semantic element types in buildings."""
    WALL = "wall"
    DOOR = "door"
    WINDOW = "window"
    SLAB = "slab"
    COLUMN = "column"
    ROOM = "room"
    LEVEL = "level"
    STAIR = "stair"
    UNKNOWN = "unknown"


class EdgeType(str, Enum):
    """Types of spatial relationships."""
    ADJACENT = "adjacent"  # Touching/sharing edge
    CONTAINED = "contained"  # Inside/contained by
    CONNECTS = "connects"  # Door connects rooms
    CIRCULATION = "circulation"  # Stair connects levels


class Level(BaseModel):
    """Building level/story."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str  # "Ground Floor", "Level 1", etc.
    elevation: float  # Absolute height
    floor_to_floor_height: Optional[float] = None  # Story height
    index: int = 0  # 0 = ground, 1 = first, etc.


class SemanticElement(BaseModel):
    """Classified CAD element with semantic type and metadata."""
    id: str  # Deterministic hash-based ID
    cad_entity_id: str  # Reference to original CadModel entity
    semantic_type: SemanticType
    layer: str
    
    # Geometry and location
    geometry_ref: Dict[str, Any]  # Pointer to entity geometry
    level_id: Optional[str] = None  # Which level it belongs to
    elevation: Optional[float] = None  # Z-coordinate or story elevation
    
    # Attributes
    attributes: Dict[str, Any] = Field(default_factory=dict)
    
    # Rule application
    rule_version: str = "1.0.0"
    confidence: float = 1.0  # 0-1 score
    rule_hits: List[str] = Field(default_factory=list)  # Which rules matched
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SpatialGraphNode(BaseModel):
    """Node in spatial graph (semantic element)."""
    node_id: str
    semantic_element_id: str
    semantic_type: SemanticType


class SpatialGraphEdge(BaseModel):
    """Edge in spatial graph (relationship between elements)."""
    from_node_id: str
    to_node_id: str
    edge_type: EdgeType
    confidence: float = 1.0
    meta: Dict[str, Any] = Field(default_factory=dict)


class SpatialGraph(BaseModel):
    """Complete spatial topology of semantic elements."""
    nodes: List[SpatialGraphNode] = Field(default_factory=list)
    edges: List[SpatialGraphEdge] = Field(default_factory=list)
    
    # Metadata
    adjacency_edge_count: int = 0
    containment_edge_count: int = 0
    connectivity_edge_count: int = 0
    graph_hash: Optional[str] = None


class SemanticModel(BaseModel):
    """Complete semantic model derived from CadModel."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    
    # Source reference
    cad_model_id: str  # Parent CadModel ID
    
    # Semantic data
    elements: List[SemanticElement] = Field(default_factory=list)
    levels: List[Level] = Field(default_factory=list)
    spatial_graph: SpatialGraph = Field(default_factory=SpatialGraph)
    
    # Validation info
    warnings: List[str] = Field(default_factory=list)
    
    # Statistics
    element_count_by_type: Dict[str, int] = Field(default_factory=dict)
    level_count: int = 0
    
    # Rules and versioning
    rule_version: str = "1.0.0"
    rule_overrides: Dict[str, Any] = Field(default_factory=dict)
    adapter_version: str = "1.0.0"
    
    # Determinism
    model_hash: Optional[str] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    meta: Dict[str, Any] = Field(default_factory=dict)


class SemanticRequest(BaseModel):
    """Request to classify and build semantics for a CAD model."""
    cad_model_id: str
    rule_version: Optional[str] = None
    rule_overrides: Dict[str, Any] = Field(default_factory=dict)
    tenant_id: str
    env: str
    user_id: Optional[str] = None


class SemanticResponse(BaseModel):
    """Response from semantic classification."""
    semantic_artifact_id: str
    semantic_model_id: str
    element_count: int
    level_count: int
    wall_count: int
    door_count: int
    window_count: int
    slab_count: int
    column_count: int
    room_count: int = 0
    stair_count: int = 0
    unknown_count: int
    graph_edge_count: int
    spatial_graph_edge_count: Optional[int] = None
    rule_version: str
    created_at: datetime
    meta: Dict[str, Any] = Field(default_factory=dict)

