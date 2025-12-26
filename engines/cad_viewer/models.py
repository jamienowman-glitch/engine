"""Pydantic models for CAD viewer view-models (Gantt + Overlay)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GanttTask(BaseModel):
    id: str
    name: str
    trade: Optional[str] = None
    level: Optional[str] = None
    zone: Optional[str] = None
    start_date: Optional[str] = None  # ISO date
    end_date: Optional[str] = None  # ISO date
    duration_days: Optional[float] = None
    predecessors: List[str] = Field(default_factory=list)
    boq_refs: List[str] = Field(default_factory=list)
    cost_refs: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)
    hash: Optional[str] = None


class CadGanttView(BaseModel):
    project_id: str
    cad_model_id: str
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    tasks: List[GanttTask] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)
    view_hash: Optional[str] = None


class OverlayElement(BaseModel):
    id: str
    name: str
    level: Optional[str] = None
    zone: Optional[str] = None
    trade: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    cost: Optional[float] = None
    boq_ref: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)
    hash: Optional[str] = None


class CadOverlayView(BaseModel):
    project_id: str
    cad_model_id: str
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    elements: List[OverlayElement] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)
    view_hash: Optional[str] = None
