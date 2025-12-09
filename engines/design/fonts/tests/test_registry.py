from __future__ import annotations

import pytest

from engines.design.fonts.registry import get_font, get_preset, to_css_tokens, tracking_to_em


def test_get_font_and_preset():
    font = get_font("roboto_flex")
    assert font.display_name == "Roboto Flex"
    preset = get_preset("roboto_flex", "regular")
    assert preset.wght == 400


def test_unknown_font_raises():
    with pytest.raises(KeyError):
        get_font("unknown_font")


def test_unknown_preset_raises():
    with pytest.raises(KeyError):
        get_preset("roboto_flex", "nope")


def test_tracking_clamp_and_tokens():
    font = get_font("roboto_flex")
    em = tracking_to_em(font, 999)
    assert em <= 0.1001
    tokens = to_css_tokens("roboto_flex", "regular", 50)
    assert "fontVariationSettings" in tokens
    assert tokens["fontFamily"].startswith("\"Roboto Flex\"")
