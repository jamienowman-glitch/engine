"""Chat service skeleton (C-01.B)."""
from __future__ import annotations

from fastapi import APIRouter

from engines.chat.service.schemas import ChatPostRequest, ChatPostResponse
from engines.chat.service.types import ChatMessageOut, ChatState

router = APIRouter()


@router.get("/chat/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/chat/{surfaceId}/{conversationId}", response_model=ChatPostResponse)
def post_message(surfaceId: str, conversationId: str, payload: ChatPostRequest) -> ChatPostResponse:
    # Hardcoded response with echoes; no business logic yet.
    message = ChatMessageOut(
        tenantId=payload.tenantId,
        env=payload.env,
        surface=surfaceId,
        conversationId=conversationId,
        messageId=payload.messageId,
        response=f"ack:{payload.message}",
        state=ChatState(phase="message", temperatureBand=payload.controls.temperatureBand if payload.controls else "neutral"),
    )
    return ChatPostResponse(message=message)
