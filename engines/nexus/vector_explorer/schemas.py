"""Schemas for Vector Explorer queries and results."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class QueryMode(str, Enum):
    all = "all"
    similar_to_id = "similar_to_id"
    similar_to_text = "similar_to_text"


class VectorExplorerQuery(BaseModel):
    tenant_id: str = Field(..., pattern=r"^t_[a-z0-9_-]+$")
    env: str
    space: str
    tags: List[str] = Field(default_factory=list)
    metadata_filters: Dict[str, Any] = Field(default_factory=dict)
    query_mode: QueryMode = QueryMode.all
    limit: int = Field(20, ge=1, le=200)
    anchor_id: Optional[str] = None
    query_text: Optional[str] = None
    trace_id: str = Field(default_factory=lambda: uuid4().hex)


class VectorExplorerItem(BaseModel):
    id: str
    label: str
    tags: List[str] = Field(default_factory=list)
    metrics: Dict[str, float] = Field(default_factory=dict)
    height_score: Optional[float] = None
    cluster_id: Optional[str] = None
    similarity_score: Optional[float] = None
    source_ref: Dict[str, Any] = Field(default_factory=dict)
    vector_ref: Optional[str] = None


class VectorExplorerResult(BaseModel):
    items: List[VectorExplorerItem]
    tenant_id: str
    env: str
    trace_id: str = Field(default_factory=lambda: uuid4().hex)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
