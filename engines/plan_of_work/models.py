"""
Plan-of-Works Models - Task and project planning structures.

Defines:
- PlanTask: Individual task with duration, dependencies, resources
- PlanDependency: Task sequencing relationships
- PlanOfWork: Complete project plan with critical path
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TaskCategory(str, Enum):
    """Task categories in building construction."""
    FOUNDATION = "foundation"
    STRUCTURE = "structure"
    ENVELOPE = "envelope"
    MEP = "mep"  # Mechanical, Electrical, Plumbing
    FINISHES = "finishes"
    DOORS_WINDOWS = "doors_windows"
    TESTING = "testing"
    HANDOVER = "handover"


class DependencyType(str, Enum):
    """Types of task dependencies."""
    FINISH_TO_START = "finish_to_start"  # Standard predecessor
    START_TO_START = "start_to_start"  # Can overlap


class PlanDependency(BaseModel):
    """Dependency relationship between tasks."""
    predecessor_task_id: str
    successor_task_id: str
    dependency_type: DependencyType = DependencyType.FINISH_TO_START
    lag_days: float = 0.0  # Delay between tasks


class PlanTask(BaseModel):
    """Single task in the plan of work."""
    id: str  # Deterministic hash-based ID
    
    # Task description
    name: str
    description: str
    category: TaskCategory
    
    # Scheduling
    duration_days: float
    dependencies: List[PlanDependency] = Field(default_factory=list)
    
    # Resources and cost
    resource_tags: List[str] = Field(default_factory=list)
    cost_refs: List[str] = Field(default_factory=list)  # Cost item IDs
    boq_refs: List[str] = Field(default_factory=list)  # BoQ item IDs
    
    # Derived during planning
    early_start_day: float = 0.0
    early_finish_day: float = 0.0
    late_start_day: Optional[float] = None
    late_finish_day: Optional[float] = None
    float_days: Optional[float] = None
    is_critical: bool = False
    
    # Metadata
    calc_version: str = "1.0.0"
    template_used: str = ""
    productivity_assumption: str = ""
    meta: Dict[str, Any] = Field(default_factory=dict)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PlanOfWork(BaseModel):
    """Complete plan of work with task graph and scheduling."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    
    # Source reference
    cost_model_id: str
    
    # Tasks and sequencing
    tasks: List[PlanTask] = Field(default_factory=list)
    all_dependencies: List[PlanDependency] = Field(default_factory=list)
    
    # Project summary
    critical_path_duration_days: float = 0.0
    critical_path_task_ids: List[str] = Field(default_factory=list)
    total_float_days: float = 0.0
    
    # Statistics
    task_count: int = 0
    task_count_by_category: Dict[str, int] = Field(default_factory=dict)
    
    # Metadata
    template_version: str = "1.0.0"
    productivity_config: Dict[str, float] = Field(default_factory=dict)
    calc_version: str = "1.0.0"
    model_hash: Optional[str] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    meta: Dict[str, Any] = Field(default_factory=dict)


class PlanRequest(BaseModel):
    """Request to generate plan from cost data."""
    cost_model_id: str
    template_version: Optional[str] = None
    productivity_config: Dict[str, float] = Field(default_factory=dict)
    tenant_id: Optional[str] = None
    env: Optional[str] = None


class PlanResponse(BaseModel):
    """Response from plan generation."""
    plan_artifact_id: str
    plan_model_id: str
    task_count: int
    task_count_by_category: Dict[str, int]
    critical_path_duration_days: float
    model_hash: str
    template_version: str
    created_at: datetime
    meta: Dict[str, Any] = Field(default_factory=dict)
