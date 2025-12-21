"""Core chat types (C-01.A)."""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Env(str, Enum):
    dev = "dev"
    stage = "stage"
    prod = "prod"


class ChatControls(BaseModel):
    temperatureBand: str = Field(default="neutral")
    strategyLock: bool = False


class ChatState(BaseModel):
    phase: str = Field(default="message")
    temperatureBand: str = Field(default="neutral")


class ChatMessageIn(BaseModel):
    tenantId: str = Field(..., pattern=r"^t_[a-z0-9_-]+$")
    env: Env
    surface: str
    conversationId: str
    messageId: str
    message: str
    controls: Optional[ChatControls] = None
    context: Optional[dict] = None


class ChatMessageOut(BaseModel):
    tenantId: str
    env: Env
    surface: str
    conversationId: str
    messageId: str
    response: str
    state: ChatState = Field(default_factory=ChatState)
    actions: List[str] = Field(default_factory=list)
