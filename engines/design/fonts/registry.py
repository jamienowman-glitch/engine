from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, Optional

from engines.design.fonts.types import AxisBounds, FontConfig, FontPreset


class FontRegistry:
    def __init__(self, fonts_dir: Optional[Path] = None):
        self.fonts_dir = fonts_dir or Path(__file__).parent
        self._fonts: Dict[str, FontConfig] = {}
        self._load_all()

    def _load_all(self) -> None:
        for json_file in sorted(self.fonts_dir.glob("*.json")):
            config = self._load_font_config(json_file)
            self._fonts[config.font_id.lower()] = config

    def _load_font_config(self, json_path: Path) -> FontConfig:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        axes = {
            axis_name: AxisBounds(**axis_data)
            for axis_name, axis_data in data.get("axes", {}).items()
        }
        data["axes"] = axes
        data["presets"] = {
            name: FontPreset(**preset_data)
            for name, preset_data in data.get("presets", {}).items()
        }
        return FontConfig(**data)

    def get_font(self, font_id: str) -> FontConfig:
        normalized = font_id.lower()
        if normalized in self._fonts:
            return self._fonts[normalized]
        raise KeyError(f"Font data not found for {font_id}")

    def list_fonts(self) -> Iterable[FontConfig]:
        return self._fonts.values()

    def find_by_name(self, name: str) -> FontConfig:
        normalized = name.lower()
        for config in self._fonts.values():
            if config.display_name.lower() == normalized or config.font_id.lower() == normalized:
                return config
        raise KeyError(f"Font not registered: {name}")

    def get_preset(self, font_id: str, preset_code: str) -> FontPreset:
        font = self.get_font(font_id)
        if preset_code not in font.presets:
            if font.presets:
                return next(iter(font.presets.values()))
            raise KeyError(f"Preset {preset_code} not found for font {font_id}")
        return font.presets[preset_code]

    def resolve_axis_values(
        self, font_id: str, preset_code: str, overrides: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        overrides = overrides or {}
        font = self.get_font(font_id)
        preset = self.get_preset(font_id, preset_code)
        axis_values = preset.axis_values()
        for axis, override_value in overrides.items():
            bounds = font.axes.get(axis)
            if bounds:
                axis_values[axis] = bounds.clamp(override_value)
            elif axis in axis_values:
                axis_values[axis] = override_value
        return axis_values

    @staticmethod
    def tracking_to_em(font: FontConfig, tracking: int) -> float:
        clamped = max(font.tracking_min_design, min(font.tracking_max_design, tracking))
        span = font.tracking_max_design - font.tracking_min_design or 1
        normalized = (clamped - font.tracking_min_design) / span  # 0..1
        return -0.1 + normalized * 0.2


_FONT_REGISTRY = FontRegistry()


def get_font_registry() -> FontRegistry:
    return _FONT_REGISTRY


def get_font(font_id: str) -> FontConfig:
    return _FONT_REGISTRY.get_font(font_id)


def get_preset(font_id: str, preset_code: str) -> FontPreset:
    return _FONT_REGISTRY.get_preset(font_id, preset_code)


def tracking_to_em(font: FontConfig, tracking: int) -> float:
    return FontRegistry.tracking_to_em(font, tracking)


def resolve_variation_settings(
    font_id: str, preset_code: str, overrides: Optional[Dict[str, float]] = None
) -> Dict[str, float]:
    return _FONT_REGISTRY.resolve_axis_values(font_id, preset_code, overrides)


def to_css_tokens(font_id: str, preset_code: str, tracking: int) -> Dict[str, str]:
    font = get_font(font_id)
    axis_values = resolve_variation_settings(font_id, preset_code, None)
    letter_spacing = tracking_to_em(font, tracking)
    variation_settings = ", ".join(f"'{k}' {v}" for k, v in sorted(axis_values.items()))
    return {
        "fontFamily": font.css_family_name,
        "fontVariationSettings": variation_settings,
        "letterSpacing": f"{letter_spacing:.4f}em",
    }
