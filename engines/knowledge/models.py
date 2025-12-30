"""Data models used by the knowledge store."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class KnowledgeScope:
    tenant_id: str
    mode: str
    project_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    def scope_parts(self) -> tuple[str, ...]:
        parts = [self.tenant_id, self.mode, self.project_id]
        if self.user_id:
            parts.append(self.user_id)
        if self.session_id:
            parts.append(self.session_id)
        return tuple(parts)


@dataclass
class KnowledgeDocument:
    doc_id: str
    scope: KnowledgeScope
    title: Optional[str]
    text: str
    metadata: Dict[str, Any]
    raw_path: str
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "tenant_id": self.scope.tenant_id,
            "mode": self.scope.mode,
            "project_id": self.scope.project_id,
            "user_id": self.scope.user_id,
            "session_id": self.scope.session_id,
            "title": self.title,
            "text": self.text,
            "metadata": self.metadata,
            "raw_path": self.raw_path,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> KnowledgeDocument:
        scope = KnowledgeScope(
            tenant_id=data["tenant_id"],
            mode=data["mode"],
            project_id=data["project_id"],
            user_id=data.get("user_id"),
            session_id=data.get("session_id"),
        )
        created_at = datetime.fromisoformat(data.get("created_at")) if data.get("created_at") else datetime.utcnow()
        return cls(
            doc_id=data["doc_id"],
            scope=scope,
            title=data.get("title"),
            text=data.get("text", ""),
            metadata=data.get("metadata") or {},
            raw_path=data.get("raw_path", ""),
            created_at=created_at,
        )
