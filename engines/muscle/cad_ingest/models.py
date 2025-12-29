"""
CAD Ingest Models - Core data structures for CAD file parsing and normalization.

Defines:
- CadIngestRequest: API request for file upload or URI
- CadModel: Normalized CAD representation with entities, topology, and healing metadata
- Entity types: Line, Arc, Polyline, Solid, etc.
- TopologyGraph: Connected graph of entities
- HealingAction: Record of topology fixes applied
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class UnitKind(str, Enum):
    """Supported unit systems."""
    MILLIMETER = "mm"
    CENTIMETER = "cm"
    METER = "m"
    FOOT = "ft"
    INCH = "in"


class EntityType(str, Enum):
    """Primitive entity types in CAD models."""
    LINE = "line"
    ARC = "arc"
    CIRCLE = "circle"
    POLYLINE = "polyline"
    POLYGON = "polygon"
    SOLID = "solid"
    SURFACE = "surface"
    BLOCK_INSTANCE = "block_instance"


class HealingActionKind(str, Enum):
    """Types of topology healing operations performed."""
    GAP_CLOSE = "gap_close"
    VERTEX_DEDUP = "vertex_dedup"
    WINDING_NORMALIZE = "winding_normalize"
    SNAP_TO_GRID = "snap_to_grid"
    DUPLICATE_REMOVE = "duplicate_remove"


class Vector3(BaseModel):
    """3D vector."""
    x: float
    y: float
    z: float = 0.0


class BoundingBox(BaseModel):
    """Axis-aligned bounding box."""
    min: Vector3
    max: Vector3


class HealingAction(BaseModel):
    """Record of a topology healing operation."""
    kind: HealingActionKind
    affected_entities: List[str] = Field(default_factory=list)
    description: str
    severity: Literal["info", "warning", "error"] = "info"


class Layer(BaseModel):
    """CAD layer/level info."""
    name: str
    visible: bool = True
    frozen: bool = False
    locked: bool = False
    color: Optional[str] = None  # e.g. "#FF0000"
    meta: Dict[str, Any] = Field(default_factory=dict)


class Entity(BaseModel):
    """Base entity in CAD model."""
    id: str  # Deterministic hash-based ID
    type: EntityType
    layer: str
    source_id: Optional[str] = None  # Original ID from source file
    geometry: Dict[str, Any]  # Type-specific geometry payload
    bbox: BoundingBox
    meta: Dict[str, Any] = Field(default_factory=dict)


class TopologyEdge(BaseModel):
    """Edge in topology graph connecting two entities."""
    from_entity_id: str
    to_entity_id: str
    edge_type: str  # "adjacent", "connected", "contained"
    distance: float = 0.0


class TopologyGraph(BaseModel):
    """Spatial and logical connectivity graph of entities."""
    entities: Dict[str, str] = Field(default_factory=dict)  # entity_id -> entity.type
    edges: List[TopologyEdge] = Field(default_factory=list)
    isolated_entities: List[str] = Field(default_factory=list)


class CadModel(BaseModel):
    """Normalized CAD model representation."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    units: UnitKind
    origin: Vector3 = Field(default_factory=lambda: Vector3(x=0, y=0, z=0))
    bbox: BoundingBox
    
    # Core data
    layers: List[Layer] = Field(default_factory=list)
    entities: List[Entity] = Field(default_factory=list)
    topology: TopologyGraph = Field(default_factory=TopologyGraph)
    
    # Healing & provenance
    healing_actions: List[HealingAction] = Field(default_factory=list)
    
    # Metadata
    source_format: Literal["dxf", "ifc-lite", "unknown"] = "unknown"
    source_sha256: Optional[str] = None
    adapter_version: str = "1.0.0"
    tolerance: float = 0.001  # Default tolerance for healing
    model_hash: Optional[str] = None  # Hash of normalized model for caching
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    meta: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("tolerance")
    @classmethod
    def tolerance_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("tolerance must be positive")
        return v


class CadIngestRequest(BaseModel):
    """Request to ingest a CAD file."""
    file_uri: Optional[str] = None  # For uploaded files, set after storage
    source_uri: Optional[str] = None  # Original source URL
    format_hint: Optional[Literal["dxf", "ifc-lite"]] = None
    unit_hint: Optional[UnitKind] = None
    tolerance: float = 0.001
    snap_to_grid: bool = False
    grid_size: float = 0.001
    max_file_size_mb: float = 100.0
    max_timeout_s: float = 30.0
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class CadIngestResponse(BaseModel):
    """Response from CAD ingest operation."""
    cad_model_artifact_id: str
    model_id: str
    units: UnitKind
    entity_count: int
    layer_count: int
    healing_actions_count: int
    bbox: BoundingBox
    model_hash: str
    source_sha256: Optional[str]
    created_at: datetime
    meta: Dict[str, Any] = Field(default_factory=dict)
