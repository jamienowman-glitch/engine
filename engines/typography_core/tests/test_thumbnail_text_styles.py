import io
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from engines.media_v2.models import MediaUploadRequest
from engines.media_v2.service import MediaService, InMemoryMediaRepository, LocalMediaStorage
from engines.typography_core.models import TextLayoutRequest
from engines.typography_core.renderer import TextLayoutMetadata, TextLayoutResult, TypographyRenderer
from engines.typography_core.service import TypographyService


class TestThumbnailTextStyles(unittest.TestCase):
    def setUp(self):
        repo = InMemoryMediaRepository()
        storage = LocalMediaStorage()
        self.media_service = MediaService(repo=repo, storage=storage)
        self.service = TypographyService(media_service=self.media_service)
        self.text_image = Image.new("RGBA", (160, 80), (0, 0, 0, 0))
        draw = ImageDraw.Draw(self.text_image)
        draw.rectangle((30, 20, 130, 60), fill=(255, 255, 255, 255))
        self.metadata = TextLayoutMetadata(
            font_family="Inter",
            font_id="roboto_flex",
            font_path="/fake",
            font_size_px=60,
            font_preset="regular",
            variation_axes={},
            tracking=0,
            alignment="left",
            width=self.text_image.width,
            height=self.text_image.height,
            line_height_px=50.0,
            line_count=1,
            layout_hash="hash123",
        )

    def _fake_render(self, req):
        return TextLayoutResult(image=self.text_image.copy(), metadata=self.metadata)

    @patch.object(TypographyRenderer, "render")
    def test_headline_overlay_and_glow_pixels(self, mock_render):
        mock_render.side_effect = self._fake_render
        req = TextLayoutRequest(
            text="NO CODE MAN",
            font_size_px=60,
            color_hex="#FFFFFF",
            color_overlay_hex="#FF0000",
            color_overlay_opacity=0.5,
            outer_glow_color_hex="#00FF00",
            outer_glow_opacity=0.75,
            outer_glow_radius_ratio=0.03,
        )
        artifact_id, asset_id, layout_meta = self.service.render_text_with_metadata(
            req, tenant_id="t", env="dev"
        )
        artifact = self.media_service.get_artifact(artifact_id)
        self.assertIsNotNone(artifact)
        output = Image.open(artifact.uri)
        center_pixel = output.getpixel((80, 40))
        self.assertGreater(center_pixel[0], 200)
        self.assertLess(center_pixel[1], 200)
        self.assertGreater(center_pixel[3], 0)
        glow_found = any(
            output.getpixel((x, y))[1] > 0 and output.getpixel((x, y))[3] > 0
            for x in range(0, 40)
            for y in range(0, 40)
        )
        self.assertTrue(glow_found)
        self.assertGreater(layout_meta.width, 0)
        self.assertGreater(layout_meta.height, 0)


if __name__ == "__main__":
    unittest.main()
