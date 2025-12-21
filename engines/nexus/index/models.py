"""Indexing data models."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SearchEntry(BaseModel):
    """Entry to be indexed."""
    id: str
    text: str
    metadata: Dict[str, Any]


class SearchResult(BaseModel):
    """Search result item."""
    id: str
    score: float
    metadata: Dict[str, Any]
    snippet: Optional[str] = None


class SearchQuery(BaseModel):
    """Search query parameters."""
    query_text: str = Field(..., description="Query text to search for")
    filters: Optional[Dict[str, Any]] = Field(None, description="Metadata key-value filters")
    top_k: int = Field(10, description="Max results to return")
    # tenant_id/env derived from RequestContext
