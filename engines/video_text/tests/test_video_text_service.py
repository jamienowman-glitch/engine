import unittest
from unittest.mock import MagicMock

from PIL import Image

from engines.media_v2.models import MediaAsset
from engines.video_text.models import TextRenderRequest
from engines.video_text.service import VideoTextService
from engines.typography_core.renderer import TextLayoutMetadata, TextLayoutResult


class TestVideoTextService(unittest.TestCase):
    def setUp(self):
        self.mock_media = MagicMock()
        self.mock_asset = MediaAsset(id="asset123", tenant_id="t1", env="dev", kind="image", source_uri="/tmp/fake.png")
        self.mock_media.register_remote.return_value = self.mock_asset
        self.mock_renderer = MagicMock()

    def test_render_text_basic(self):
        image = Image.new("RGBA", (128, 64), (255, 255, 255, 255))
        metadata = TextLayoutMetadata(
            font_family="Inter",
            font_id="roboto_flex",
            font_path="/fake",
            font_size_px=64,
            font_preset="regular",
            variation_axes={"wght": 400},
            tracking=0,
            alignment="left",
            width=128,
            height=64,
            line_height_px=64.0,
            line_count=1,
            layout_hash="hash123",
        )
        self.mock_renderer.render.return_value = TextLayoutResult(image=image, metadata=metadata)

        service = VideoTextService(media_service=self.mock_media, renderer=self.mock_renderer)

        req = TextRenderRequest(
            tenant_id="t1",
            env="dev",
            text="Hello",
            font_size_px=32,
            color_hex="#FF0000",
            width=128,
            height=64,
        )

        resp = service.render_text_image(req)

        self.assertEqual(resp.asset_id, "asset123")
        self.assertEqual(resp.uri, "/tmp/fake.png")
        self.assertEqual(resp.width, 128)
        self.assertEqual(resp.height, 64)
        self.assertEqual(resp.meta["font_family"], "Inter")
        self.assertEqual(resp.meta["layout_hash"], "hash123")
        self.assertEqual(resp.meta["variant_axes"], {"wght": 400})
        self.mock_renderer.render.assert_called_once()
        self.mock_media.register_remote.assert_called_once()

    def test_render_empty_text(self):
        service = VideoTextService(media_service=self.mock_media, renderer=self.mock_renderer)
        req = TextRenderRequest(tenant_id="t1", env="dev", text="")
        with self.assertRaises(ValueError):
            service.render_text_image(req)


if __name__ == "__main__":
    unittest.main()
