"""Schemas for 3-Wise LLM engine (G-01.B)."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel


class ThreeWiseCheckRequest(BaseModel):
    tenantId: str
    env: str
    prompt: str
    surface: str
    conversationId: str


class ThreeWiseVote(BaseModel):
    model: str
    risk: float
    notes: str = ""


class ThreeWiseCheckResult(BaseModel):
    votes: List[ThreeWiseVote]
    aggregate_risk: float
