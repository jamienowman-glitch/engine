"""Research Run models."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ResearchRun(BaseModel):
    """
    Represents a discrete 'run' or interaction within Nexus.
    Derived from aggregating DatasetEvents.
    """
    run_id: str = Field(description="Unique ID of the run (often trace_id)")
    tenant_id: str
    env: str
    
    # Aggregated fields
    start_time: datetime
    end_time: datetime
    status: str = "completed" # derived
    
    kind: str = Field(description="Ingest, Search, Pack, Index, etc.")
    
    # Counts
    events_count: int = 0
    cards_count: int = 0
    atoms_count: int = 0
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
