from __future__ import annotations

from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field


class TextLayoutRequest(BaseModel):
    text: str
    font_family: str = "Inter"
    font_preset: str = "regular"
    font_size_px: int = 100
    line_height_multiplier: float = 1.2
    tracking: int = 0  # design units based letterspacing

    # Layout box
    width: Optional[int] = None  # Wrapping width in pixels
    height: Optional[int] = None

    alignment: Literal["left", "center", "right"] = "left"
    color_hex: str = "#FFFFFF"

    variation_settings: Dict[str, float] = Field(default_factory=dict)  # e.g. {"wght": 700}
