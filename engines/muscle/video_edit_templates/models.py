from __future__ import annotations
import uuid
from typing import List, Dict, Optional, Any, Literal
from pydantic import BaseModel, Field

class TemplateSlot(BaseModel):
    id: str
    description: str

class ClipBlueprint(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    slot_id: str
    start_ms: float
    duration_ms: float
    # Optional constraints or effects
    effects: List[Dict[str, Any]] = Field(default_factory=list)

class TrackBlueprint(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    kind: Literal["video", "audio"] = "video"
    clips: List[ClipBlueprint] = Field(default_factory=list)

class EditTemplate(BaseModel):
    id: str
    name: str
    slots: List[TemplateSlot] = Field(default_factory=list)
    tracks: List[TrackBlueprint] = Field(default_factory=list)
