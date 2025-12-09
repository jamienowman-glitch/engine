"""Data contracts for universal chat stubs (PLAN-024)."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ChatScope(BaseModel):
    surface: str | None = None
    app: str | None = None
    federation: str | None = None
    cluster: str | None = None
    gang: str | None = None
    agent: str | None = None
    # Legacy fallback for minimal scopes
    kind: str | None = None  # surface | app | federation | cluster | gang | agent
    target_id: str | None = None

    def tags(self) -> list[str]:
        tags: list[str] = []
        for key in ["surface", "app", "federation", "cluster", "gang", "agent"]:
            value = getattr(self, key)
            if value:
                tags.extend([key, value])
        if self.kind:
            tags.append(self.kind)
        if self.target_id:
            tags.append(self.target_id)
        return tags


class Contact(BaseModel):
    id: str
    display_name: Optional[str] = None
    handle: Optional[str] = None


class Message(BaseModel):
    id: str
    thread_id: str
    sender: Contact
    text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    role: str = "user"  # user | agent | system
    scope: ChatScope | None = None


class Thread(BaseModel):
    id: str
    participants: List[Contact] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    title: Optional[str] = None
