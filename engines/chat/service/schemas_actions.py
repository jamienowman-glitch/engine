"""Schemas for chat message actions (C-01.C)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from engines.chat.service.types import Env


class BaseActionRequest(BaseModel):
    tenantId: str
    env: Env
    surface: str
    conversationId: str
    messageId: Optional[str] = None


class StrategyLockRequest(BaseActionRequest):
    scope: str
    confirm: bool = False


class ThreeWiseCheckRequest(BaseActionRequest):
    prompt: str


class PromptExpandRequest(BaseActionRequest):
    prompt: str


class NexusIngestRequest(BaseActionRequest):
    uri: str


class ReminderCreateRequest(BaseActionRequest):
    text: str
    when: str


class UndoRequest(BaseActionRequest):
    targetMessageId: str


class TodoCreateRequest(BaseActionRequest):
    text: str


class ActionResponse(BaseModel):
    status: str = "accepted"
    stub: bool = True
    action: str
