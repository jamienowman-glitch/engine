import unittest
from unittest.mock import MagicMock, patch
from PIL import Image, ImageColor
import io
from engines.image_core.models import ImageComposition, ImageLayer
from engines.image_core.backend import ImageCoreBackend
from engines.image_core.service import ImageCoreService
from engines.media_v2.models import MediaAsset, DerivedArtifact
from engines.media_v2.service import MediaService, InMemoryMediaRepository, LocalMediaStorage

class TestI01Composite(unittest.TestCase):
    def setUp(self):
        self.mock_media_service = MagicMock()
        self.backend = ImageCoreBackend(self.mock_media_service)

    def test_solid_color_layer(self):
        comp = ImageComposition(
            tenant_id="t", env="e", 
            width=100, height=100, 
            background_color="#FF0000" # Red bg
        )
        # Blue layer
        layer = ImageLayer(color="#0000FF", width=50, height=50, x=0, y=0)
        comp.layers.append(layer)
        
        png_bytes = self.backend.render(comp)
        
        # Verify
        img = Image.open(io.BytesIO(png_bytes))
        self.assertEqual(img.size, (100, 100))
        # Top left should be blue (layer)
        self.assertEqual(img.getpixel((0,0)), (0, 0, 255, 255))
        # Bottom right should be red (bg)
        self.assertEqual(img.getpixel((99,99)), (255, 0, 0, 255))

    def test_opacity(self):
        comp = ImageComposition(
            tenant_id="t", env="e",
            width=100, height=100, background_color="#000000"
        ) # Black
        # White layer 50% opacity
        layer = ImageLayer(color="#FFFFFF", width=100, height=100, opacity=0.5)
        comp.layers.append(layer)
        
        png_bytes = self.backend.render(comp)
        img = Image.open(io.BytesIO(png_bytes))
        
        px = img.getpixel((50,50))
        self.assertTrue(0 < px[0] < 255)
        self.assertEqual(px[3], 255)

    def test_basic_adjustments_mock(self):
        # We can't easily test visual output of adjustments without reference images,
        # but we can ensure it runs without error.
        comp = ImageComposition(
            tenant_id="t", env="e",
            width=100, height=100
        )
        layer = ImageLayer(color="#808080", adjustments={"contrast": 2.0})
        comp.layers.append(layer)
        
        try:
            self.backend.render(comp)
        except Exception as e:
            self.fail(f"Render with adjustments failed: {e}")

    def test_pipeline_hash_ignores_layer_ids(self):
        comp_a = ImageComposition(tenant_id="t", env="e", width=50, height=50)
        comp_a.layers.append(ImageLayer(color="#101010", x=0, y=0))
        comp_b = ImageComposition(tenant_id="t", env="e", width=50, height=50)
        comp_b.layers.append(ImageLayer(color="#101010", x=0, y=0))
        hash_a = self.backend.compute_pipeline_hash(comp_a)
        hash_b = self.backend.compute_pipeline_hash(comp_b)
        self.assertEqual(hash_a, hash_b)

    def test_service_records_pipeline_meta(self):
        mock_media = MagicMock()
        mock_media.register_upload.return_value = MediaAsset(id="asset", tenant_id="t", env="e", kind="image", source_uri="/tmp/image.png")
        mock_media.register_artifact.return_value = DerivedArtifact(id="image_art", parent_asset_id="asset", tenant_id="t", env="e", kind="image_render", uri="uri")

        service = ImageCoreService(media_service=mock_media)
        service.backend.render = MagicMock(return_value=b"bytes")
        service.backend.compute_pipeline_hash = MagicMock(return_value="hash123")

        comp = ImageComposition(tenant_id="t", env="e", width=10, height=10)
        comp.layers.append(ImageLayer(color="#FFFFFF"))

        art_id = service.render_composition(comp)
        self.assertEqual(art_id, "image_art")

        artifact_req = mock_media.register_artifact.call_args[0][0]
        self.assertEqual(artifact_req.meta["pipeline_hash"], "hash123")
        self.assertIn("blend_modes", artifact_req.meta)

    def test_backend_deterministic_render_bytes(self):
        backend = ImageCoreBackend(MagicMock())
        comp = ImageComposition(tenant_id="t", env="e", width=32, height=32)
        comp.layers.append(ImageLayer(color="#FFFFFF", width=32, height=32))
        comp.layers.append(ImageLayer(color="#FF0000", x=8, y=8, width=16, height=16))
        h = backend.compute_pipeline_hash(comp)
        b1 = backend.render(comp, pipeline_hash=h)
        b2 = backend.render(comp, pipeline_hash=h)
        self.assertEqual(b1, b2)

    def test_blend_modes_affect_output(self):
        backend = ImageCoreBackend(MagicMock())
        comp1 = ImageComposition(tenant_id="t", env="e", width=32, height=32, background_color="#777777")
        comp1.layers.append(ImageLayer(color="#4444FF", x=8, y=8, width=16, height=16, blend_mode="normal"))
        comp2 = ImageComposition(tenant_id="t", env="e", width=32, height=32, background_color="#777777")
        comp2.layers.append(ImageLayer(color="#4444FF", x=8, y=8, width=16, height=16, blend_mode="multiply"))
        b1 = backend.render(comp1)
        b2 = backend.render(comp2)
        self.assertNotEqual(b1, b2)

    def test_service_invalid_opacity_raises(self):
        mock_media = MagicMock()
        service = ImageCoreService(media_service=mock_media)
        comp = ImageComposition(tenant_id="t", env="e", width=10, height=10)
        comp.layers.append(ImageLayer(color="#FFFFFF", opacity=2.5))
        with self.assertRaises(ValueError):
            service.render_composition(comp)

    def test_render_with_preset_registers_format(self):
        repo = InMemoryMediaRepository()
        storage = LocalMediaStorage()
        media_svc = MediaService(repo=repo, storage=storage)
        svc = ImageCoreService(media_service=media_svc)

        comp = ImageComposition(
            tenant_id="t1",
            env="test",
            width=200,
            height=200,
            layers=[
                ImageLayer(name="bg", color="#FFFFFFFF", width=200, height=200),
                ImageLayer(name="red", color="#FF0000FF", x=50, y=50, width=100, height=100, opacity=1.0),
            ],
        )

        art_id = svc.render_composition(comp, preset_id="web_small")
        art = media_svc.get_artifact(art_id)
        self.assertIsNotNone(art)
        self.assertEqual(art.meta.get("preset_id"), "web_small")
        self.assertEqual(art.meta.get("format"), "WEBP")

    def test_render_with_unknown_preset_raises(self):
        mock_media = MagicMock()
        service = ImageCoreService(media_service=mock_media)
        comp = ImageComposition(tenant_id="t", env="e", width=10, height=10)
        with self.assertRaises(ValueError):
            service.render_composition(comp, preset_id="no_such_preset")

if __name__ == '__main__':
    unittest.main()
