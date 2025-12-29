"""
BoQ Quantities Models - Bill of Quantities item schemas.

Defines:
- BoQItem: Quantity item (type, quantity, unit, scope, source refs)
- Scope: Level/zone tagging with totals
- BoQModel: Complete bill of quantities with items and scopes
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class UnitType(str, Enum):
    """Quantity units."""
    # Length
    MM = "mm"
    CM = "cm"
    M = "m"
    FT = "ft"
    IN = "in"
    
    # Area
    MM2 = "mm²"
    CM2 = "cm²"
    M2 = "m²"
    FT2 = "ft²"
    
    # Volume
    MM3 = "mm³"
    CM3 = "cm³"
    M3 = "m³"
    FT3 = "ft³"
    
    # Count
    COUNT = "count"
    NO = "no"


class FormulaType(str, Enum):
    """Types of quantity formulas."""
    WALL_LENGTH = "wall_length"
    WALL_AREA = "wall_area"
    WALL_AREA_NET = "wall_area_net"  # With openings deducted
    SLAB_AREA = "slab_area"
    SLAB_VOLUME = "slab_volume"
    COLUMN_COUNT = "column_count"
    COLUMN_VOLUME = "column_volume"
    COLUMN_LENGTH = "column_length"
    DOOR_COUNT = "door_count"
    DOOR_AREA = "door_area"
    WINDOW_COUNT = "window_count"
    WINDOW_AREA = "window_area"
    ROOM_AREA = "room_area"
    ROOM_PERIMETER = "room_perimeter"
    OPENING_AREA = "opening_area"
    UNKNOWN = "unknown"


class Scope(BaseModel):
    """Scope/zone/level grouping."""
    scope_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    scope_name: str  # "Ground Floor", "Zone A", etc.
    level_id: Optional[str] = None  # Reference to semantic level
    zone_tag: Optional[str] = None  # Custom zone/room tag
    
    # Totals per scope
    item_count: int = 0
    total_area: Optional[float] = None
    total_volume: Optional[float] = None
    total_length: Optional[float] = None
    total_count: int = 0


class BoQItem(BaseModel):
    """Single bill of quantities item."""
    id: str  # Deterministic hash-based ID
    
    # Classification
    element_type: Literal["wall", "door", "window", "slab", "column", "room", "stair", "opening", "unknown"]
    
    # Quantity data
    quantity: float
    unit: UnitType
    quantity_in_original_units: Optional[float] = None  # For reference
    original_unit: Optional[UnitType] = None
    
    # Location & scope
    level_id: Optional[str] = None
    scope_id: Optional[str] = None
    zone_tag: Optional[str] = None
    
    # Source & formula
    source_element_ids: List[str] = Field(default_factory=list)  # semantic element IDs
    source_cad_entity_ids: List[str] = Field(default_factory=list)  # CAD entity IDs
    formula_used: FormulaType
    calc_version: str = "1.0.0"
    
    # Details
    attributes: Dict[str, Any] = Field(default_factory=dict)
    meta: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BoQModel(BaseModel):
    """Complete bill of quantities."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    
    # Source reference
    semantic_model_id: str
    
    # BoQ data
    items: List[BoQItem] = Field(default_factory=list)
    scopes: List[Scope] = Field(default_factory=list)
    
    # Statistics
    item_count: int = 0
    item_count_by_type: Dict[str, int] = Field(default_factory=dict)
    
    # Rules and versioning
    calc_version: str = "1.0.0"
    calc_params: Dict[str, Any] = Field(default_factory=dict)  # Thickness defaults, tolerances, etc.
    adapter_version: str = "1.0.0"
    
    # Determinism
    model_hash: Optional[str] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    meta: Dict[str, Any] = Field(default_factory=dict)


class BoQRequest(BaseModel):
    """Request to generate BoQ from semantic model."""
    semantic_model_id: str
    calc_version: Optional[str] = None
    calc_params: Dict[str, Any] = Field(default_factory=dict)
    tenant_id: Optional[str] = None
    env: Optional[str] = None


class BoQResponse(BaseModel):
    """Response from BoQ generation."""
    boq_artifact_id: str
    boq_model_id: str
    item_count: int
    item_count_by_type: Dict[str, int]
    scope_count: int
    model_hash: str
    calc_version: str
    created_at: datetime
    meta: Dict[str, Any] = Field(default_factory=dict)
