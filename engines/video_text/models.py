from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class TextRenderRequest(BaseModel):
    tenant_id: str
    env: str
    user_id: Optional[str] = None
    text: str
    font_family: str = "Inter"  # Logic in service to resolve this to file
    font_size_px: int = 100
    font_preset: str = "regular"
    tracking: int = 0
    color_hex: str = "#FFFFFF"
    width: Optional[int] = None
    height: Optional[int] = None
    variation_settings: Dict[str, float] = Field(default_factory=dict) # e.g. {"wght": 700}
    meta: Dict[str, Any] = Field(default_factory=dict)


class TextRenderResponse(BaseModel):
    asset_id: str
    uri: str
    width: int
    height: int
    meta: Dict[str, Any] = Field(default_factory=dict)
