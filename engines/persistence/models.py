"""Shared models for versioned persistence artifacts."""
from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ArtifactCreateRequest(BaseModel):
    id: Optional[str] = Field(default=None, description="Optional client-supplied id; generated if omitted")
    title: Optional[str] = None
    description: Optional[str] = None
    data: Dict[str, Any]
    surface_id: Optional[str] = None


class ArtifactUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    surface_id: Optional[str] = None


class ArtifactRecord(BaseModel):
    id: str
    tenant_id: str
    mode: str
    env: Optional[str] = None
    project_id: str
    surface_id: Optional[str] = None
    app_id: Optional[str] = None
    user_id: Optional[str] = None
    version: int
    title: Optional[str] = None
    description: Optional[str] = None
    data: Dict[str, Any]
    created_at: str
    updated_at: str
    deleted: bool = False


def generate_artifact_id() -> str:
    return uuid4().hex
