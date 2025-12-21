"""Influence Pack data models."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from engines.nexus.index.models import SearchQuery


class CardRef(BaseModel):
    """
    Reference to a Card within a Pack.
    Purely opaque reference; excerpt is debug-only.
    """
    card_id: str = Field(..., description="ID of the referenced card")
    score: float = Field(..., description="Relevance score from index")
    excerpt: Optional[str] = Field(None, description="Opaque debug snippet from index (optional)")
    artifact_refs: List[str] = Field(default_factory=list, description="IDs of artifacts referenced by the card (opague)")


class InfluencePack(BaseModel):
    """
    Budgeted container of references (Cards) relevant to a query.
    No semantic interpretation or summarization.
    """
    pack_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = Field(..., description="Tenant ID")
    env: str = Field(..., description="Environment")
    
    query: SearchQuery = Field(..., description="Query used to generate this pack")
    
    card_refs: List[CardRef] = Field(..., description="Ordered list of card references")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Operational metadata")
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = Field(None, description="User ID or Agent ID")
