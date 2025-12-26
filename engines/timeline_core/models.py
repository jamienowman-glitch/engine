"""
Timeline Core Models.

Defines the core data structures for the Agnostic Timeline Engine.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

class TaskStatus(str, Enum):
    """Status of a timeline task."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class DependencyType(str, Enum):
    """Type of dependency between tasks."""
    FINISH_TO_START = "finish_to_start"  # B starts after A finishes
    START_TO_START = "start_to_start"    # B starts after A starts
    FINISH_TO_FINISH = "finish_to_finish" # B finishes after A finishes
    START_TO_FINISH = "start_to_finish"  # B finishes after A starts


class Dependency(BaseModel):
    """
    A directed dependency between two tasks.
    """
    from_task_id: str
    to_task_id: str
    type: DependencyType = DependencyType.FINISH_TO_START
    meta: Dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
    """
    A single unit of work on the timeline.
    """
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    tenant_id: str
    env: str
    request_id: str
    
    title: str
    start_ts: datetime
    end_ts: Optional[datetime] = None
    duration_ms: Optional[float] = None
    
    status: TaskStatus = TaskStatus.TODO
    tags: List[str] = Field(default_factory=list)
    
    # Grouping for Gantt
    group_id: Optional[str] = None  # e.g. "Level 1"
    lane_id: Optional[str] = None   # e.g. "Trade: Plumbing"
    
    # Source traceability
    source_kind: Optional[str] = None # e.g. "boq_item", "cad_plan"
    source_id: Optional[str] = None
    
    meta: Dict[str, Any] = Field(default_factory=dict)
    
    @model_validator(mode='after')
    def validate_dates(self):
        if self.start_ts and self.end_ts and self.start_ts > self.end_ts:
            raise ValueError("start_ts must be <= end_ts")
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValueError("duration_ms must be non-negative")
        return self

    @staticmethod
    def generate_deterministic_id(
        tenant_id: str,
        env: str,
        source_kind: str,
        source_id: str,
        extra_discriminators: List[str] = None
    ) -> str:
        """
        Generate a deterministic ID based on upstream source.
        Rule: sha256(tenant|env|source_kind|source_id|...extras)
        """
        parts = [tenant_id, env, source_kind, source_id]
        if extra_discriminators:
            parts.extend(extra_discriminators)
        
        # Ensure consistent ordering if extras provided, but list implies order matters.
        # We assume caller provides order.
        

        raw = "|".join(parts)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ContentPlanItem(BaseModel):
    """Single item in a marketing content plan."""
    id: str  # Client provided ID
    campaign: str
    channel: str
    asset: str
    due_date: datetime
    owner: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class ContentPlanPayload(BaseModel):
    """Payload for importing a content plan."""
    items: List[ContentPlanItem]
class GanttItem(BaseModel):
    """
    Representation of a task for the Gantt Chart.
    """
    id: str
    label: str
    start: datetime
    end: datetime
    status: TaskStatus
    dependencies: List[str] = Field(default_factory=list) # List of predecessor IDs
    
    # Visuals
    color: Optional[str] = None
    progress: float = 0.0
    icon: Optional[str] = None
    tooltip: Dict[str, str] = Field(default_factory=dict)
    
    meta: Dict[str, Any] = Field(default_factory=dict)


class GanttRow(BaseModel):
    """
    A row in the Gantt chart, potentially containing sub-rows or items.
    Used for grouping (e.g. by Scope, then by Trade).
    """
    id: str
    label: str
    items: List[GanttItem] = Field(default_factory=list)
    sub_rows: List["GanttRow"] = Field(default_factory=list) # Nested rows

GanttRow.update_forward_refs()


class GanttView(BaseModel):
    """
    The full view model for a Gantt chart.
    """
    project_start: Optional[datetime] = None
    project_end: Optional[datetime] = None
    rows: List[GanttRow] = Field(default_factory=list)
    unscoped_items: List[GanttItem] = Field(default_factory=list)


