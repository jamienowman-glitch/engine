from __future__ import annotations

from typing import Dict, Iterable

from pydantic import BaseModel, Field


class AxisBounds(BaseModel):
    min: float
    max: float
    default: float

    def clamp(self, value: float) -> float:
        return max(self.min, min(self.max, value))


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

    @classmethod
    def axis_fields(cls) -> Iterable[str]:
        return (
            "opsz",
            "wght",
            "GRAD",
            "wdth",
            "slnt",
            "XOPQ",
            "YOPQ",
            "XTRA",
            "YTUC",
            "YTLC",
            "YTAS",
            "YTDE",
            "YTFI",
        )

    def axis_values(self) -> Dict[str, float]:
        return {axis: getattr(self, axis) for axis in self.axis_fields()}

    def to_variation_settings(self) -> str:
        return ", ".join(f"'{axis}' {value}" for axis, value in self.axis_values().items())


class FontConfig(BaseModel):
    font_id: str
    display_name: str
    css_family_name: str
    tracking_min_design: int
    tracking_max_design: int
    tracking_default_design: int
    primary_file_path: str
    axes: Dict[str, AxisBounds] = Field(default_factory=dict)
    presets: Dict[str, FontPreset] = Field(default_factory=dict)
