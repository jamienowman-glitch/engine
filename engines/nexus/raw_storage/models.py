"""Raw Storage data models (Pydantic)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class RawAsset(BaseModel):
    """
    Immutable raw asset record.
    
    Stored in S3 (or equivalent) at:
    tenants/<tenant_id>/<env>/raw/<asset_id>/<filename>
    """
    asset_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = Field(..., description="Tenant ID owning this asset")
    env: str = Field(..., description="Environment (dev|staging|prod)")
    uri: str = Field(..., description="Full S3/GCS URI for the blob")
    filename: str = Field(..., description="Original filename")
    sha256: Optional[str] = None
    size_bytes: Optional[int] = None
    content_type: str = "application/octet-stream"
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata (lineage)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = Field(None, description="User ID who uploaded/registered")
