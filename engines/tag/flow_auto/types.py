from __future__ import annotations

from typing import List, Dict, Any

from pydantic import BaseModel


class FlowAutoInput(BaseModel):
    bars: List[Dict[str, Any]]


class FlowPair(BaseModel):
    bar_start: int
    bar_end: int
    flow_pred: str


class FlowAutoOutput(BaseModel):
    bars: List[Dict[str, Any]]
    flow_pairs: List[FlowPair]
