from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from engines.design.fonts.types import FontConfig, FontPreset

_REGISTRY: Dict[str, FontConfig] = {}


def _load_font_json(font_id: str) -> FontConfig:
    data_path = Path(__file__).parent / f"{font_id}.json"
    if not data_path.exists():
        raise KeyError(f"Font data not found for {font_id}")
    data = json.loads(data_path.read_text(encoding="utf-8"))
    data["presets"] = {k: FontPreset(**v) for k, v in data.get("presets", {}).items()}
    return FontConfig(**data)


def get_font(font_id: str) -> FontConfig:
    if font_id not in _REGISTRY:
        _REGISTRY[font_id] = _load_font_json(font_id)
    return _REGISTRY[font_id]


def get_preset(font_id: str, preset_code: str) -> FontPreset:
    font = get_font(font_id)
    if preset_code not in font.presets:
        raise KeyError(f"Preset {preset_code} not found for font {font_id}")
    return font.presets[preset_code]


def tracking_to_em(font: FontConfig, tracking: int) -> float:
    clamped = max(font.tracking_min_design, min(font.tracking_max_design, tracking))
    # Map design units [-200..200] -> [-0.1..0.1] em
    span = font.tracking_max_design - font.tracking_min_design or 1
    normalized = (clamped - font.tracking_min_design) / span  # 0..1
    return -0.1 + normalized * 0.2


def to_css_tokens(font_id: str, preset_code: str, tracking: int) -> Dict[str, str]:
    font = get_font(font_id)
    preset = get_preset(font_id, preset_code)
    letter_spacing = tracking_to_em(font, tracking)
    return {
        "fontFamily": font.css_family_name,
        "fontVariationSettings": preset.to_variation_settings(),
        "letterSpacing": f"{letter_spacing:.4f}em",
    }
