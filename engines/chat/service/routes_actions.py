"""Stub routes for chat message actions (C-01.C)."""
from __future__ import annotations

from fastapi import APIRouter

from engines.chat.service.schemas_actions import (
    ActionResponse,
    NexusIngestRequest,
    PromptExpandRequest,
    ReminderCreateRequest,
    StrategyLockRequest,
    ThreeWiseCheckRequest,
    TodoCreateRequest,
    UndoRequest,
)

router = APIRouter(prefix="/chat/actions")


def _accept(action: str) -> ActionResponse:
    return ActionResponse(action=action)


@router.post("/strategy_lock")
def strategy_lock(req: StrategyLockRequest) -> ActionResponse:
    return _accept("strategy_lock")


@router.post("/three_wise")
def three_wise(req: ThreeWiseCheckRequest) -> ActionResponse:
    return _accept("three_wise")


@router.post("/prompt_expand")
def prompt_expand(req: PromptExpandRequest) -> ActionResponse:
    return _accept("prompt_expand")


@router.post("/nexus_ingest")
def nexus_ingest(req: NexusIngestRequest) -> ActionResponse:
    return _accept("nexus_ingest")


@router.post("/reminder_create")
def reminder_create(req: ReminderCreateRequest) -> ActionResponse:
    return _accept("reminder_create")


@router.post("/undo")
def undo(req: UndoRequest) -> ActionResponse:
    return _accept("undo")


@router.post("/todo_create")
def todo_create(req: TodoCreateRequest) -> ActionResponse:
    return _accept("todo_create")
