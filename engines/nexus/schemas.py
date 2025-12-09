"""Nexus schemas (N-01.A)."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field


class NexusKind(str, Enum):
    data = "data"
    research = "research"
    style = "style"
    content = "content"
    chat = "chat"
    plan = "plan"


class NexusDocument(BaseModel):
    id: str
    text: str
    tenant_id: Optional[str] = Field(default=None, pattern=r"^t_[a-z0-9_-]+$")
    env: Optional[str] = None
    kind: Optional[NexusKind] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    refs: Dict[str, Any] = Field(default_factory=dict)


class NexusIngestRequest(BaseModel):
    tenantId: str = Field(..., pattern=r"^t_[a-z0-9_-]+$")
    env: str
    kind: NexusKind
    docs: List[NexusDocument]

    @property
    def space(self) -> str:
        kind_value = self.kind.value if isinstance(self.kind, NexusKind) else str(self.kind)
        return f"nexus-{self.tenantId}-{kind_value}-{self.env}"


class NexusQueryRequest(BaseModel):
    tenantId: str
    env: str
    kind: NexusKind
    query: str
    top_k: int = 5


class NexusQueryResult(BaseModel):
    hits: List[NexusDocument] = Field(default_factory=list)


class NexusEmbedding(BaseModel):
    doc_id: str
    tenant_id: str = Field(..., pattern=r"^t_[a-z0-9_-]+$")
    env: str
    kind: NexusKind
    embedding: List[float]
    model_id: str
    dimensions: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NexusUsage(BaseModel):
    tenant_id: str = Field(..., pattern=r"^t_[a-z0-9_-]+$")
    env: str
    doc_ids: List[str]
    purpose: str
    agent_id: Optional[str] = None
    episode_id: Optional[str] = None
    scores: Optional[List[float]] = None
    created_at: Optional[datetime] = None
