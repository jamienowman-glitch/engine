import io
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

from engines.image_core.backend import ImageCoreBackend
from engines.image_core.models import ImageComposition, ImageLayer
from engines.typography_core.models import TextLayoutRequest
from engines.typography_core.renderer import (
    TextLayoutMetadata,
    TextLayoutResult,
    TypographyRenderer,
)


class TestI03Typography(unittest.TestCase):
    def setUp(self):
        self.renderer = TypographyRenderer()
        self.backend = ImageCoreBackend(MagicMock())
        self.font_config = MagicMock(tracking_min_design=-200, tracking_max_design=200)
        self.registry_entry = ("roboto_flex", self.font_config, "/fake/path", {"wght": 400})

    @patch("engines.typography_core.renderer.ImageDraw.Draw")
    @patch("engines.typography_core.renderer.ImageFont.truetype")
    @patch("engines.typography_core.renderer.tracking_to_em", return_value=0.0)
    def test_text_layout_basic(self, mock_tracking, mock_truetype, mock_draw_cls):
        mock_font = MagicMock()
        mock_font.getbbox.side_effect = lambda text: (0, 0, len(text) * 10, 50) if text else (0, 0, 0, 0)
        mock_font.getmetrics.return_value = (40, 10)
        mock_truetype.return_value = mock_font
        mock_draw = MagicMock()
        mock_draw_cls.return_value = mock_draw

        with patch.object(self.renderer.registry, "resolve_font_entry", return_value=self.registry_entry):
            req = TextLayoutRequest(text="Hello World", font_size_px=50, color_hex="#FF0000")
            result = self.renderer.render(req)

            self.assertIsInstance(result.image, Image.Image)
            self.assertEqual(result.image.mode, "RGBA")
            self.assertGreater(result.metadata.line_count, 0)
            self.assertEqual(result.metadata.font_family, "Inter")
            self.assertTrue(result.metadata.layout_hash)
            self.assertEqual(result.metadata.tracking, req.tracking)

    @patch("engines.typography_core.renderer.ImageDraw.Draw")
    @patch("engines.typography_core.renderer.ImageFont.truetype")
    @patch("engines.typography_core.renderer.tracking_to_em", return_value=0.0)
    def test_text_wrapping(self, mock_tracking, mock_truetype, mock_draw_cls):
        mock_font = MagicMock()
        mock_font.getbbox.side_effect = lambda text: (0, 0, len(text) * 10, 20) if text else (0, 0, 0, 0)
        mock_font.getmetrics.return_value = (18, 2)
        mock_truetype.return_value = mock_font
        mock_draw = MagicMock()
        mock_draw_cls.return_value = mock_draw

        with patch.object(self.renderer.registry, "resolve_font_entry", return_value=self.registry_entry):
            req = TextLayoutRequest(text="word word word", font_size_px=20, width=50)
            result = self.renderer.render(req)

            self.assertGreater(result.metadata.line_count, 1)
            self.assertGreater(result.image.height, 20)

    def test_image_layer_text_integration(self):
        green_image = Image.new("RGBA", (50, 50), (0, 255, 0, 255))
        metadata = TextLayoutMetadata(
            font_family="Inter",
            font_id="roboto_flex",
            font_path="/fake",
            font_size_px=50,
            font_preset="regular",
            variation_axes={},
            tracking=0,
            alignment="left",
            width=50,
            height=50,
            line_height_px=20.0,
            line_count=1,
            layout_hash="abc123",
        )
        fake_result = TextLayoutResult(image=green_image, metadata=metadata)

        with patch.object(self.backend.text_renderer, "render", return_value=fake_result) as mock_render:
            comp = ImageComposition(
                tenant_id="t",
                env="e",
                width=200,
                height=200,
                background_color="#000000",
            )
            layer = ImageLayer(text="Hi", text_color="#00FF00", text_size=50, x=0, y=0)
            comp.layers.append(layer)

            png_bytes = self.backend.render(comp)
            img = Image.open(io.BytesIO(png_bytes))

            mock_render.assert_called_once()
            args = mock_render.call_args[0][0]
            self.assertEqual(args.text, "Hi")
            self.assertEqual(args.color_hex, "#00FF00")
            self.assertEqual(args.font_preset, "regular")
            self.assertEqual(args.tracking, 0)
            self.assertEqual(args.variation_settings, {})
            self.assertEqual(img.getpixel((10, 10)), (0, 255, 0, 255))

    def test_axis_override_clamping(self):
        # Ensure that axis overrides beyond font bounds are clamped and layouts remain deterministic
        req_override = TextLayoutRequest(text="Weight test", font_family="roboto_flex", variation_settings={"wght": 99999}, font_size_px=20)
        req_clamped = TextLayoutRequest(text="Weight test", font_family="roboto_flex", variation_settings={"wght": 1000}, font_size_px=20)
        r1 = self.renderer.render(req_override)
        r2 = self.renderer.render(req_clamped)
        self.assertEqual(r1.metadata.layout_hash, r2.metadata.layout_hash)

if __name__ == "__main__":
    unittest.main()
