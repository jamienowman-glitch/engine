"""Atom Artifact data models."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AtomArtifact(BaseModel):
    """
    Derived artifact (Atom) generated deterministically from a Raw Asset.
    """
    atom_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = Field(..., description="Tenant ID owning this atom")
    env: str = Field(..., description="Environment (dev|staging|prod)")
    
    parent_asset_id: str = Field(..., description="ID of the source Raw Asset")
    
    # Payload (one of uri or content usually set)
    uri: Optional[str] = Field(None, description="URI if atom is stored as file")
    content: Optional[str] = Field(None, description="Content if atom is text/small data")
    
    op_type: str = Field(..., description="Operation type used to generate (e.g. text_identity)")
    op_version: str = Field("v1", description="Version of the operation")
    
    source_start_ms: Optional[int] = None
    source_end_ms: Optional[int] = None
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Lineage/Derivation metadata")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = Field(None, description="User ID or System Agent ID")
