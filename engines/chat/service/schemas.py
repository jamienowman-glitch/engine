"""HTTP schemas for Chat Surface (C-01.A)."""
from __future__ import annotations

from pydantic import BaseModel

from engines.chat.service.types import ChatMessageIn, ChatMessageOut


class ChatPostRequest(ChatMessageIn):
    pass


class ChatPostResponse(BaseModel):
    message: ChatMessageOut
