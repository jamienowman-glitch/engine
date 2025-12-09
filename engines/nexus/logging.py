"""Nexus logging helpers for embeddings and usage."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from engines.nexus.schemas import NexusUsage


class PromptSnapshot(BaseModel):
    text: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ModelCallLog(BaseModel):
    call_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = Field(..., pattern=r"^t_[a-z0-9_-]+$")
    env: str
    model_id: str
    purpose: str
    prompt: PromptSnapshot
    output_dimensions: int
    episode_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


ModelCallLogger = Callable[[ModelCallLog], None]
UsageLogger = Callable[[NexusUsage], None]
