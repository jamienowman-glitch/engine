"""Card data models."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class Card(BaseModel):
    """
    Card artifacts: YAML header + Natural Language body.
    """
    card_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = Field(..., description="Tenant ID owning this card")
    env: str = Field(..., description="Environment")
    
    version: str = Field("v1", description="Versioning string")
    card_type: str = Field(..., description="Type of card (e.g. kpi_definition, persona)")
    
    header: Dict[str, Any] = Field(..., description="Parsed YAML header")
    body_text: str = Field(..., description="Natural language body text")
    full_text: str = Field(..., description="Original full text content")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="System metadata (not user YAML)")
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = Field(None, description="User ID or Agent ID")
