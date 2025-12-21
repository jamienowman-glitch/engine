from __future__ import annotations

import hashlib
from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, List, Tuple

from PIL import Image, ImageColor, ImageDraw, ImageFont

from engines.design.fonts.registry import tracking_to_em
from engines.typography_core.models import TextLayoutRequest
from engines.typography_core.registry import get_font_registry


@dataclass(frozen=True)
class TextLayoutMetadata:
    font_family: str
    font_id: str
    font_path: str
    font_size_px: int
    font_preset: str
    variation_axes: Dict[str, float]
    tracking: int
    alignment: str
    width: int
    height: int
    line_height_px: float
    line_count: int
    layout_hash: str


@dataclass(frozen=True)
class TextLayoutResult:
    image: Image.Image
    metadata: TextLayoutMetadata


@dataclass
class _LayoutInfo:
    lines: List[str]
    line_widths: List[float]
    max_width: float
    line_height_px: float


class TypographyRenderer:
    def __init__(self):
        self.registry = get_font_registry()
        self._layout_cache: OrderedDict[str, _LayoutInfo] = OrderedDict()
        self._cache_limit = 128

    def render(self, req: TextLayoutRequest) -> TextLayoutResult:
        font_id, font_config, font_path, axis_values = self.registry.resolve_font_entry(
            req.font_family, req.font_preset, req.variation_settings
        )
        try:
            font = ImageFont.truetype(font_path, size=req.font_size_px)
        except OSError:
            font = ImageFont.load_default()
            font_path = "<default>"

        tracking_px = tracking_to_em(font_config, req.tracking) * req.font_size_px
        cache_key = self._build_cache_key(req, font_id, axis_values)
        layout_info = self._layout_cache.get(cache_key)
        if not layout_info:
            layout_info = self._calculate_layout(font, req, tracking_px)
            self._add_to_cache(cache_key, layout_info)
        else:
            self._layout_cache.move_to_end(cache_key)

        canvas_width, canvas_height = self._canvas_size(req, layout_info)
        image = self._draw_text(font, req, layout_info, canvas_width, canvas_height)
        layout_hash = self._compute_layout_hash(
            req,
            axis_values,
            layout_info.lines,
            layout_info.line_widths,
            layout_info.max_width,
            layout_info.line_height_px,
        )

        metadata = TextLayoutMetadata(
            font_family=req.font_family,
            font_id=font_id,
            font_path=font_path,
            font_size_px=req.font_size_px,
            font_preset=req.font_preset,
            variation_axes=dict(axis_values),
            tracking=req.tracking,
            alignment=req.alignment,
            width=canvas_width,
            height=canvas_height,
            line_height_px=layout_info.line_height_px,
            line_count=len(layout_info.lines),
            layout_hash=layout_hash,
        )

        return TextLayoutResult(image=image, metadata=metadata)

    def _build_cache_key(self, req: TextLayoutRequest, font_id: str, axis_values: Dict[str, float]) -> str:
        normalized_axes = tuple(sorted(axis_values.items()))
        parts = (
            req.text,
            font_id,
            req.font_preset,
            req.font_size_px,
            req.tracking,
            req.width,
            req.height,
            req.line_height_multiplier,
            req.alignment,
            normalized_axes,
        )
        key = hashlib.sha256(repr(parts).encode("utf-8")).hexdigest()
        return key

    def _add_to_cache(self, key: str, info: _LayoutInfo) -> None:
        self._layout_cache[key] = info
        if len(self._layout_cache) > self._cache_limit:
            self._layout_cache.popitem(last=False)

    def _calculate_layout(
        self, font: ImageFont.FreeTypeFont, req: TextLayoutRequest, tracking_px: float
    ) -> _LayoutInfo:
        lines = self._wrap_text(req, font, tracking_px)
        line_widths = [self._measure_line(line, font, tracking_px) for line in lines]
        max_width = max(line_widths) if line_widths else 0
        line_height_px = self._line_height(font, req.line_height_multiplier)
        return _LayoutInfo(lines=lines, line_widths=line_widths, max_width=max_width, line_height_px=line_height_px)

    def _wrap_text(self, req: TextLayoutRequest, font: ImageFont.FreeTypeFont, tracking_px: float) -> List[str]:
        if not req.text:
            return [""]

        wrap_width = req.width
        lines: List[str] = []
        for raw_line in req.text.splitlines():
            if wrap_width is None:
                lines.append(raw_line)
                continue
            current_words: List[str] = []
            for word in raw_line.split(" "):
                if not word and current_words:
                    current_words.append("")
                    continue
                candidate = " ".join(current_words + [word]).strip()
                candidate = candidate or word
                width = self._measure_line(candidate, font, tracking_px)
                if width <= wrap_width:
                    current_words.append(word)
                else:
                    if current_words:
                        lines.append(" ".join(current_words).strip())
                        current_words = [word]
                    else:
                        lines.append(word)
                        current_words = []
            if current_words:
                lines.append(" ".join(current_words).strip())
            elif not raw_line and not lines:
                lines.append("")
        if not lines:
            lines.append("")
        return lines

    def _measure_line(self, line: str, font: ImageFont.FreeTypeFont, tracking_px: float) -> float:
        if not line:
            return 0.0
        try:
            bbox = font.getbbox(line)
            width = bbox[2] - bbox[0]
        except Exception:
            width = font.getsize(line)[0]
        spacing = max(len(line) - 1, 0) * tracking_px
        return width + spacing

    def _line_height(self, font: ImageFont.FreeTypeFont, multiplier: float) -> float:
        try:
            ascent, descent = font.getmetrics()
            base_height = ascent + descent
        except Exception:
            bbox = font.getbbox("Mg")
            base_height = bbox[3] - bbox[1]
        return base_height * multiplier

    def _compute_layout_hash(
        self,
        req: TextLayoutRequest,
        axis_values: Dict[str, float],
        lines: List[str],
        line_widths: List[float],
        max_width: float,
        line_height_px: float,
    ) -> str:
        payload = (
            req.text,
            req.font_family,
            req.font_preset,
            req.font_size_px,
            req.tracking,
            req.width,
            req.height,
            req.alignment,
            tuple(sorted(axis_values.items())),
            tuple(lines),
            tuple(line_widths),
            max_width,
            line_height_px,
        )
        return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()

    def _draw_text(
        self,
        font: ImageFont.FreeTypeFont,
        req: TextLayoutRequest,
        info: _LayoutInfo,
        canvas_width: int,
        canvas_height: int,
    ) -> Image.Image:
        img = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        color = ImageColor.getrgb(req.color_hex)
        y = 0.0
        for index, line in enumerate(info.lines):
            width = info.line_widths[index] if index < len(info.line_widths) else 0.0
            x = 0.0
            if req.alignment == "center":
                x = (canvas_width - width) / 2
            elif req.alignment == "right":
                x = max(canvas_width - width, 0)
            draw.text((x, y), line, font=font, fill=color)
            y += info.line_height_px
        return img

    def _canvas_size(self, req: TextLayoutRequest, info: _LayoutInfo) -> Tuple[int, int]:
        width = req.width if req.width else max(int(info.max_width + 4), 1)
        height = req.height if req.height else max(
            int(len(info.lines) * info.line_height_px + 4), int(info.line_height_px)
        )
        return width, height
