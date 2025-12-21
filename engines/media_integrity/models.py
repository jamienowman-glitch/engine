from __future__ import annotations
from typing import List, Literal, Optional, Dict
from pydantic import BaseModel, Field

IntegrityStatus = Literal["OK", "CORRUPT", "WARNING"]

class StreamInfo(BaseModel):
    index: int
    codec_type: str # video, audio
    codec_name: str
    width: Optional[int] = None
    height: Optional[int] = None
    pix_fmt: Optional[str] = None
    color_space: Optional[str] = None
    duration: Optional[float] = None

class IntegrityReport(BaseModel):
    asset_id: str
    status: IntegrityStatus
    streams: List[StreamInfo] = Field(default_factory=list)
    messages: List[str] = Field(default_factory=list)
    meta: Dict[str, str] = Field(default_factory=dict)
