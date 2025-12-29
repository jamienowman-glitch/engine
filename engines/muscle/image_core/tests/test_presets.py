import unittest
from PIL import Image
import io
from engines.image_core.models import ImageComposition, ImageLayer
from engines.image_core.service import ImageCoreService
from engines.media_v2.service import MediaService, InMemoryMediaRepository, LocalMediaStorage

class TestPresets(unittest.TestCase):
    def setUp(self):
        repo = InMemoryMediaRepository()
        storage = LocalMediaStorage()
        self.media_svc = MediaService(repo=repo, storage=storage)
        self.svc = ImageCoreService(media_service=self.media_svc)

    def _open_asset_image(self, artifact_id):
        art = self.media_svc.get_artifact(artifact_id)
        self.assertIsNotNone(art)
        path = art.uri
        img = Image.open(path)
        return img

    def test_instagram_1080_and_web_large_and_thumbnail(self):
        comp = ImageComposition(tenant_id="t", env="test", width=3000, height=2000)
        comp.layers.append(ImageLayer(color="#FF0000FF", width=3000, height=2000))

        art_id_inst = self.svc.render_composition(comp, preset_id="instagram_1080")
        img_inst = self._open_asset_image(art_id_inst)
        self.assertEqual(img_inst.format.upper(), "JPEG")
        self.assertEqual(img_inst.size, (1080, 1080))

        art_id_web = self.svc.render_composition(comp, preset_id="web_large")
        img_web = self._open_asset_image(art_id_web)
        # web_large requests width=2048, height preserved by aspect
        self.assertEqual(img_web.format.upper(), "WEBP")
        self.assertEqual(img_web.size[0], 2048)

        art_id_thumb = self.svc.render_composition(comp, preset_id="thumbnail_200")
        img_thumb = self._open_asset_image(art_id_thumb)
        self.assertEqual(img_thumb.format.upper(), "PNG")
        self.assertEqual(img_thumb.size, (200, 200))

    def test_tiff_and_print_a4(self):
        comp = ImageComposition(tenant_id="t", env="test", width=1200, height=800)
        comp.layers.append(ImageLayer(color="#00FF00FF", width=1200, height=800))

        art_id_tiff = self.svc.render_composition(comp, preset_id="tiff_high_quality")
        img_tiff = self._open_asset_image(art_id_tiff)
        self.assertEqual(img_tiff.format.upper(), "TIFF")
        # tiff preset does not resize; should match original
        self.assertEqual(img_tiff.size, (1200, 800))

        comp2 = ImageComposition(tenant_id="t", env="test", width=3000, height=2000)
        comp2.layers.append(ImageLayer(color="#0000FF", width=3000, height=2000))
        art_id_print = self.svc.render_composition(comp2, preset_id="print_a4_300dpi")
        img_print = self._open_asset_image(art_id_print)
        self.assertEqual(img_print.format.upper(), "JPEG")
        self.assertEqual(img_print.size, (2480, 3508))

    def test_social_story_presets(self):
        """Test vertical story presets (Instagram story, TikTok, Snapchat)."""
        comp = ImageComposition(tenant_id="t", env="test", width=1080, height=1920)
        comp.layers.append(ImageLayer(color="#FF6600FF", width=1080, height=1920))

        art_id_ig = self.svc.render_composition(comp, preset_id="instagram_story_1080x1920")
        img_ig = self._open_asset_image(art_id_ig)
        self.assertEqual(img_ig.format.upper(), "WEBP")
        self.assertEqual(img_ig.size, (1080, 1920))

        art_id_tiktok = self.svc.render_composition(comp, preset_id="tiktok_video_1080x1920")
        img_tiktok = self._open_asset_image(art_id_tiktok)
        self.assertEqual(img_tiktok.format.upper(), "WEBP")
        self.assertEqual(img_tiktok.size, (1080, 1920))

        art_id_snap = self.svc.render_composition(comp, preset_id="snapchat_story_1080x1920")
        img_snap = self._open_asset_image(art_id_snap)
        self.assertEqual(img_snap.format.upper(), "WEBP")
        self.assertEqual(img_snap.size, (1080, 1920))

    def test_ecommerce_product_presets(self):
        """Test e-commerce product image presets."""
        comp = ImageComposition(tenant_id="t", env="test", width=2000, height=2000)
        comp.layers.append(ImageLayer(color="#FFFFFFFF", width=2000, height=2000))

        art_id_400 = self.svc.render_composition(comp, preset_id="ecommerce_product_400x400")
        img_400 = self._open_asset_image(art_id_400)
        self.assertEqual(img_400.format.upper(), "PNG")
        self.assertEqual(img_400.size, (400, 400))

        art_id_800 = self.svc.render_composition(comp, preset_id="ecommerce_product_800x800")
        img_800 = self._open_asset_image(art_id_800)
        self.assertEqual(img_800.format.upper(), "PNG")
        self.assertEqual(img_800.size, (800, 800))

        art_id_1200 = self.svc.render_composition(comp, preset_id="ecommerce_gallery_1200x1200")
        img_1200 = self._open_asset_image(art_id_1200)
        self.assertEqual(img_1200.format.upper(), "JPEG")
        self.assertEqual(img_1200.size, (1200, 1200))

    def test_avatar_icon_presets(self):
        """Test avatar and icon presets."""
        comp = ImageComposition(tenant_id="t", env="test", width=512, height=512)
        comp.layers.append(ImageLayer(color="#3366CCFF", width=512, height=512))

        art_id_64 = self.svc.render_composition(comp, preset_id="avatar_64x64")
        img_64 = self._open_asset_image(art_id_64)
        self.assertEqual(img_64.format.upper(), "PNG")
        self.assertEqual(img_64.size, (64, 64))

        art_id_256 = self.svc.render_composition(comp, preset_id="icon_256x256")
        img_256 = self._open_asset_image(art_id_256)
        self.assertEqual(img_256.format.upper(), "PNG")
        self.assertEqual(img_256.size, (256, 256))

    def test_display_presets(self):
        """Test display/screen presets."""
        comp = ImageComposition(tenant_id="t", env="test", width=3440, height=1440)
        comp.layers.append(ImageLayer(color="#222222FF", width=3440, height=1440))

        art_id_hd = self.svc.render_composition(comp, preset_id="desktop_1920x1080")
        img_hd = self._open_asset_image(art_id_hd)
        self.assertEqual(img_hd.format.upper(), "WEBP")
        self.assertEqual(img_hd.size, (1920, 1080))

        art_id_2k = self.svc.render_composition(comp, preset_id="desktop_2560x1440")
        img_2k = self._open_asset_image(art_id_2k)
        self.assertEqual(img_2k.format.upper(), "WEBP")
        self.assertEqual(img_2k.size, (2560, 1440))

        art_id_ultra = self.svc.render_composition(comp, preset_id="ultrawide_3440x1440")
        img_ultra = self._open_asset_image(art_id_ultra)
        self.assertEqual(img_ultra.format.upper(), "WEBP")
        self.assertEqual(img_ultra.size, (3440, 1440))

    def test_ad_presets(self):
        """Test advertising banner presets."""
        comp = ImageComposition(tenant_id="t", env="test", width=728, height=90)
        comp.layers.append(ImageLayer(color="#FF0000FF", width=728, height=90))

        art_id_728 = self.svc.render_composition(comp, preset_id="google_ads_728x90")
        img_728 = self._open_asset_image(art_id_728)
        self.assertEqual(img_728.format.upper(), "JPEG")
        self.assertEqual(img_728.size, (728, 90))

        comp2 = ImageComposition(tenant_id="t", env="test", width=300, height=250)
        comp2.layers.append(ImageLayer(color="#00FF00FF", width=300, height=250))
        art_id_300 = self.svc.render_composition(comp2, preset_id="google_ads_300x250")
        img_300 = self._open_asset_image(art_id_300)
        self.assertEqual(img_300.format.upper(), "JPEG")
        self.assertEqual(img_300.size, (300, 250))

    def test_email_presets(self):
        """Test email content presets."""
        comp = ImageComposition(tenant_id="t", env="test", width=600, height=200)
        comp.layers.append(ImageLayer(color="#0099FFFF", width=600, height=200))

        art_id_header = self.svc.render_composition(comp, preset_id="email_header_600x200")
        img_header = self._open_asset_image(art_id_header)
        self.assertEqual(img_header.format.upper(), "JPEG")
        self.assertEqual(img_header.size, (600, 200))

    def test_print_presets(self):
        """Test print presets with DPI."""
        comp = ImageComposition(tenant_id="t", env="test", width=1200, height=1800)
        comp.layers.append(ImageLayer(color="#FFCCCCFF", width=1200, height=1800))

        art_id_postcard = self.svc.render_composition(comp, preset_id="print_postcard_4x6_300dpi")
        img_postcard = self._open_asset_image(art_id_postcard)
        self.assertEqual(img_postcard.format.upper(), "JPEG")
        self.assertEqual(img_postcard.size, (1200, 1800))

    def test_draft_presets(self):
        """Test draft/preview presets with lower quality."""
        comp = ImageComposition(tenant_id="t", env="test", width=1920, height=1080)
        comp.layers.append(ImageLayer(color="#888888FF", width=1920, height=1080))

        art_id_480 = self.svc.render_composition(comp, preset_id="draft_preview_480")
        img_480 = self._open_asset_image(art_id_480)
        self.assertEqual(img_480.format.upper(), "WEBP")
        self.assertEqual(img_480.size[0], 480)

        art_id_720 = self.svc.render_composition(comp, preset_id="draft_preview_720")
        img_720 = self._open_asset_image(art_id_720)
        self.assertEqual(img_720.format.upper(), "WEBP")
        self.assertEqual(img_720.size[0], 720)

if __name__ == '__main__':
    unittest.main()

