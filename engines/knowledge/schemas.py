"""Request/response schemas for knowledge routes."""
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class KnowledgeIngestRequest(BaseModel):
    text: str
    title: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    doc_id: Optional[str] = None


class KnowledgeQueryRequest(BaseModel):
    query_text: str
    limit: int = Field(default=5, ge=1, le=50)
