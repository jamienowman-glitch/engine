"""
CAD Diff Models - Change tracking and impact analysis structures.

Defines:
- ElementDiff: Added/removed/modified semantic elements
- BoQDelta: Quantity changes per item
- CostDelta: Cost impact changes
- TaskImpact: Affected tasks in plan
- CadDiff: Complete diff report
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    """Types of changes detected."""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


class SeverityLevel(str, Enum):
    """Change severity for impact assessment."""
    CRITICAL = "critical"  # Structural/safety impact
    HIGH = "high"  # Significant quantity/cost change
    MEDIUM = "medium"  # Moderate impact
    LOW = "low"  # Cosmetic or minor change
    NONE = "none"  # No impact


class ElementDiff(BaseModel):
    """Diff record for a semantic element."""
    element_id: str
    element_type: str
    change_type: ChangeType
    
    # Old and new values
    old_attributes: Dict[str, Any] = Field(default_factory=dict)
    new_attributes: Dict[str, Any] = Field(default_factory=dict)
    attribute_changes: Dict[str, tuple] = Field(default_factory=dict)  # key -> (old, new)
    
    # Geometry changes
    geometry_changed: bool = False
    layer_changed: bool = False
    
    # Severity and impact
    severity: SeverityLevel
    impact_tags: List[str] = Field(default_factory=list)  # e.g., ["cost_impact", "schedule_impact"]


class BoQDelta(BaseModel):
    """Change in BoQ due to element modification."""
    boq_item_id: str
    boq_item_type: str
    
    # Quantity change
    old_quantity: float
    new_quantity: float
    quantity_delta: float
    
    # Unit and scope
    unit: str
    scope_id: Optional[str] = None
    
    # Impact
    severity: SeverityLevel
    affected_by_element_ids: List[str] = Field(default_factory=list)


class CostDelta(BaseModel):
    """Change in cost estimate."""
    cost_item_id: str
    boq_item_id: str
    
    # Cost change
    old_cost: float
    new_cost: float
    cost_delta: float
    
    # Currency
    currency: str
    
    # Impact
    severity: SeverityLevel
    affected_by_boq_ids: List[str] = Field(default_factory=list)


class TaskImpact(BaseModel):
    """Impact on plan-of-works task."""
    task_id: str
    task_name: str
    
    # Schedule impact
    old_duration_days: float
    new_duration_days: float
    duration_delta_days: float
    
    # Critical path impact
    critical_path_impact: bool
    old_critical: bool
    new_critical: bool
    
    # Dependencies affected
    affected_by_cost_ids: List[str] = Field(default_factory=list)
    affected_by_boq_ids: List[str] = Field(default_factory=list)
    
    severity: SeverityLevel


class CadDiff(BaseModel):
    """Complete diff report between artifact versions."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    
    # Source versions
    old_artifact_id: str
    old_artifact_type: str  # "cad_semantics", "boq_quantities", "boq_cost", "plan_of_work"
    new_artifact_id: str
    new_artifact_type: str
    
    # Element-level changes
    element_diffs: List[ElementDiff] = Field(default_factory=list)
    added_count: int = 0
    removed_count: int = 0
    modified_count: int = 0
    
    # Impact summary
    boq_deltas: List[BoQDelta] = Field(default_factory=list)
    cost_deltas: List[CostDelta] = Field(default_factory=list)
    task_impacts: List[TaskImpact] = Field(default_factory=list)
    
    # Statistics
    total_changes: int = 0
    critical_change_count: int = 0
    max_severity: SeverityLevel = SeverityLevel.NONE
    
    # Metadata
    calc_version: str = "1.0.0"
    model_hash: Optional[str] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    meta: Dict[str, Any] = Field(default_factory=dict)


class DiffRequest(BaseModel):
    """Request to compute diff between artifact versions."""
    old_artifact_id: str
    old_artifact_type: str
    new_artifact_id: str
    new_artifact_type: str
    calc_version: Optional[str] = None
    tenant_id: Optional[str] = None
    env: Optional[str] = None


class DiffResponse(BaseModel):
    """Response from diff computation."""
    diff_artifact_id: str
    diff_model_id: str
    total_changes: int
    added_count: int
    removed_count: int
    modified_count: int
    critical_change_count: int
    max_severity: SeverityLevel
    model_hash: str
    created_at: datetime
    meta: Dict[str, Any] = Field(default_factory=dict)
