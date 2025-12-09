from __future__ import annotations

from typing import Dict

from pydantic import BaseModel, Field


class FontPreset(BaseModel):
    opsz: float
    wght: float
    GRAD: float
    wdth: float
    slnt: float
    XOPQ: float
    YOPQ: float
    XTRA: float
    YTUC: float
    YTLC: float
    YTAS: float
    YTDE: float
    YTFI: float

    def to_variation_settings(self) -> str:
        return (
            f\"'opsz' {self.opsz}, 'wght' {self.wght}, 'GRAD' {self.GRAD}, "
            f\"'wdth' {self.wdth}, 'slnt' {self.slnt}, 'XOPQ' {self.XOPQ}, 'YOPQ' {self.YOPQ}, "
            f\"'XTRA' {self.XTRA}, 'YTUC' {self.YTUC}, 'YTLC' {self.YTLC}, 'YTAS' {self.YTAS}, "
            f\"'YTDE' {self.YTDE}, 'YTFI' {self.YTFI}\"
        )


class FontConfig(BaseModel):
    font_id: str
    display_name: str
    css_family_name: str
    tracking_min_design: int
    tracking_max_design: int
    tracking_default_design: int
    primary_file_path: str
    presets: Dict[str, FontPreset] = Field(default_factory=dict)
