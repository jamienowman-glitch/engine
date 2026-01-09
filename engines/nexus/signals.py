"""Nexus signals and event models (E-02)."""
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

from engines.nexus.schemas import NexusDocument, NexusKind

class IngestRequest(BaseModel):
    """Event payload for ingestion requests."""
    space_id: str
    tenant_id: str
    items: List[Dict[str, Any]]  # Raw items before normalization
    trace_id: str = Field(default_factory=lambda: "unknown")
