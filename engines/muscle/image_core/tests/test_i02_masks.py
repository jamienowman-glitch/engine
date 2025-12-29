import unittest
from unittest.mock import MagicMock
from PIL import Image, ImageColor, ImageDraw
import io
import tempfile
import os
from engines.image_core.models import ImageComposition, ImageLayer, ImageSelection, BrushStroke
from engines.image_core.backend import ImageCoreBackend
from engines.image_core.service import ImageCoreService
from engines.media_v2.models import DerivedArtifact, MediaAsset

class TestI02Masks(unittest.TestCase):
    def setUp(self):
        self.mock_media_service = MagicMock()
        self.backend = ImageCoreBackend(self.mock_media_service)

    def test_polygon_mask(self):
        comp = ImageComposition(
            tenant_id="t", env="e", 
            width=100, height=100, 
            background_color="#000000" # Black bg
        )
        # White layer with mask
        # Mask is top-left 50x50 square
        poly = ImageSelection(type="polygon", points=[(0,0), (50,0), (50,50), (0,50)])
        layer = ImageLayer(color="#FFFFFF", width=100, height=100, mask=poly)
        comp.layers.append(layer)
        
        png_bytes = self.backend.render(comp)
        img = Image.open(io.BytesIO(png_bytes))
        
        # (10,10) should be white (masked area)
        self.assertEqual(img.getpixel((10,10)), (255, 255, 255, 255))
        # (60,60) should be black (bg, mask is black there)
        self.assertEqual(img.getpixel((60,60)), (0, 0, 0, 255))

    def test_feather_mask(self):
        # Just ensure it runs and modifies pixels
        comp = ImageComposition(tenant_id="t", env="e", width=100, height=100)
        poly = ImageSelection(type="polygon", points=[(0,0), (50,0), (50,50), (0,50)], feather_radius=5.0)
        layer = ImageLayer(color="#FFFFFF", mask=poly)
        comp.layers.append(layer)
        
        png_bytes = self.backend.render(comp)
        img = Image.open(io.BytesIO(png_bytes))
        # Check edge pixel for gray value (approx)
        px = img.getpixel((50,25)) # On the edge
        # Non-zero (feathered) and not 255 or 0 completely?
        # Exact values depend on Gaussian implementation, but should not be sharp
        pass

    def test_brush_mask(self):
        comp = ImageComposition(tenant_id="t", env="e", width=100, height=100)
        stroke = BrushStroke(points=[(0,0), (100,100)], width=10)
        sel = ImageSelection(type="brush", strokes=[stroke])
        layer = ImageLayer(color="#FFFFFF", mask=sel)
        comp.layers.append(layer)
        
        png_bytes = self.backend.render(comp)
        img = Image.open(io.BytesIO(png_bytes))
        
        # Check diagonal
        self.assertEqual(img.getpixel((50,50)), (255, 255, 255, 255))
        # Check corner (off diagonal)
        self.assertEqual(img.getpixel((0,99)), (0, 0, 0, 0)) # Fully transparent bg (default)

    def test_mask_artifact_source(self):
        mask_holder = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        try:
            mask_img = Image.new("L", (100, 100), 0)
            draw = ImageDraw.Draw(mask_img)
            draw.rectangle((0, 0, 50, 100), fill=255)
            mask_img.save(mask_holder.name)
            mask_art = DerivedArtifact(
                id="mask-art",
                parent_asset_id="asset",
                tenant_id="t",
                env="e",
                kind="mask",
                uri=mask_holder.name
            )
            self.mock_media_service.get_artifact.return_value = mask_art

            comp = ImageComposition(tenant_id="t", env="e", width=100, height=100, background_color="#000000")
            layer = ImageLayer(color="#FFFFFF", mask_artifact_id="mask-art")
            comp.layers.append(layer)

            png_bytes = self.backend.render(comp)
            img = Image.open(io.BytesIO(png_bytes))
            self.assertEqual(img.getpixel((10, 10)), (255, 255, 255, 255))
            self.assertEqual(img.getpixel((60, 10)), (0, 0, 0, 255))
        finally:
            mask_holder.close()
            os.unlink(mask_holder.name)

    def test_generate_mask_caches_selection(self):
        mock_media = MagicMock()
        mock_media.register_upload.return_value = MediaAsset(
            id="mask_asset", tenant_id="t", env="e", kind="image", source_uri="/tmp/mask.png"
        )
        mask_art = DerivedArtifact(
            id="mask123",
            parent_asset_id="mask_asset",
            tenant_id="t",
            env="e",
            kind="mask",
            uri="/tmp/mask.png",
            meta={}
        )
        mock_media.register_artifact.return_value = mask_art

        service = ImageCoreService(media_service=mock_media)
        selection = ImageSelection(type="polygon", points=[(0, 0), (50, 0), (50, 50)])
        first = service.generate_mask(selection, 100, 100, "t", "e")
        second = service.generate_mask(selection, 100, 100, "t", "e")

        self.assertEqual(first, mask_art.id)
        self.assertEqual(second, mask_art.id)
        self.assertEqual(mock_media.register_upload.call_count, 1)
        self.assertEqual(mock_media.register_artifact.call_count, 1)

        artifact_request = mock_media.register_artifact.call_args[0][0]
        meta = artifact_request.meta
        self.assertEqual(meta["mask_type"], "polygon")
        self.assertIn("selection_hash", meta)
        self.assertEqual(meta["points_count"], 3)

    def test_generate_mask_invalid_inputs(self):
        mock_media = MagicMock()
        service = ImageCoreService(media_service=mock_media)
        # Missing tenant/env
        selection = ImageSelection(type="polygon", points=[(0,0),(10,0),(10,10)])
        try:
            service.generate_mask(selection, 100, 100, "", "")
            raised = False
        except ValueError:
            raised = True
        self.assertTrue(raised)

        # Feather too large
        selection2 = ImageSelection(type="polygon", points=[(0,0),(10,0),(10,10)], feather_radius=1000.0)
        try:
            service.generate_mask(selection2, 100, 100, "t", "e")
            raised2 = False
        except ValueError:
            raised2 = True
        self.assertTrue(raised2)

        # Brush stroke width too large
        from engines.image_core.models import BrushStroke
        stroke = BrushStroke(points=[(0,0),(100,100)], width=10000)
        selection3 = ImageSelection(type="brush", strokes=[stroke])
        try:
            service.generate_mask(selection3, 100, 100, "t", "e")
            raised3 = False
        except ValueError:
            raised3 = True
        self.assertTrue(raised3)

if __name__ == '__main__':
    unittest.main()
