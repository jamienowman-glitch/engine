from __future__ import annotations
from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel, Field

PreviewStrategy = Literal["DRAFT", "HQ"]

class PreviewRequest(BaseModel):
    sequence_id: str
    strategy: PreviewStrategy = "DRAFT"
    bbox_width: int = 480 # Default low res
    bbox_height: int = -2 # Maintain aspect

class PreviewResult(BaseModel):
    sequence_id: str
    render_plan: Dict[str, Any]
    estimated_latency_ms: int
