"""Schemas for Strategy Lock engine (G-01.A)."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel


class StrategyScope(BaseModel):
    objective: str
    constraints: List[str] = []


class StrategyDraft(BaseModel):
    summary: str
    steps: List[str] = []


class StrategyDecision(BaseModel):
    approved: bool
    notes: str = ""
    draft: StrategyDraft
