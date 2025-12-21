from __future__ import annotations

from pathlib import Path
from typing import Dict

from engines.design.fonts.registry import get_font_registry, resolve_variation_settings
from engines.design.fonts.types import FontConfig


class TypographyFontRegistry:
    def __init__(self):
        self._design_registry = get_font_registry()
        self._font_base = Path(__file__).resolve().parents[1] / "design"
        self._family_map: Dict[str, str] = {}
        self._default_font_id = None
        self._build_family_map()

    def _build_family_map(self) -> None:
        fonts = list(self._design_registry.list_fonts())
        if not fonts:
            raise RuntimeError("No fonts registered in design registry")
        self._default_font_id = fonts[0].font_id
        for config in fonts:
            self._family_map[config.font_id.lower()] = config.font_id
            self._family_map[config.display_name.lower()] = config.font_id

    def resolve_font_id(self, family_name: str) -> str:
        if not family_name:
            return self._default_font_id
        return self._family_map.get(family_name.lower(), self._default_font_id)

    def get_font_path(self, font_id: str) -> str:
        config = self._design_registry.get_font(font_id)
        return str((self._font_base / config.primary_file_path).resolve())

    def get_font_config(self, font_id: str) -> FontConfig:
        return self._design_registry.get_font(font_id)

    def resolve_variation(
        self, font_family: str, preset_code: str, overrides: Dict[str, float]
    ) -> Dict[str, float]:
        font_id = self.resolve_font_id(font_family)
        return resolve_variation_settings(font_id, preset_code, overrides)

    def resolve_font_entry(
        self, font_family: str, preset_code: str, overrides: Dict[str, float]
    ):
        font_id = self.resolve_font_id(font_family)
        axis_values = resolve_variation_settings(font_id, preset_code, overrides)
        font_config = self.get_font_config(font_id)
        font_path = self.get_font_path(font_id)
        return font_id, font_config, font_path, axis_values


_FONT_REGISTRY = TypographyFontRegistry()


def get_font_registry() -> TypographyFontRegistry:
    return _FONT_REGISTRY
