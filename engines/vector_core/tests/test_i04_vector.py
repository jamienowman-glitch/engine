import unittest
from unittest.mock import MagicMock
from PIL import Image
import io
from engines.media_v2.models import MediaAsset, DerivedArtifact
from engines.vector_core.models import (
    VectorScene,
    RectNode,
    CircleNode,
    VectorStyle,
    BooleanOperation,
)
from engines.vector_core.renderer import VectorRenderer
from engines.vector_core.svg_parser import SVGParser, SVGExporter
from engines.image_core.models import ImageComposition, ImageLayer
from engines.image_core.backend import ImageCoreBackend
from engines.vector_core.service import VectorService

class TestI04Vector(unittest.TestCase):
    def setUp(self):
        self.renderer = VectorRenderer()
        self.backend = ImageCoreBackend(MagicMock())

    def test_render_primitives(self):
        scene = VectorScene(width=100, height=100, tenant_id="t", env="e")
        rect = RectNode(width=50, height=50, style=VectorStyle(fill_color="#FF0000"))
        scene.root.children.append(rect)
        
        img = self.renderer.render(scene)
        
        self.assertEqual(img.width, 100)
        self.assertEqual(img.height, 100)
        # Check red pixel at 10,10
        self.assertEqual(img.getpixel((10,10)), (255, 0, 0, 255))
        # Check empty at 60,60
        self.assertEqual(img.getpixel((60,60)), (0, 0, 0, 0))

    def test_svg_roundtrip(self):
        # Basic SVG
        svg_content = '<svg width="100.0" height="100.0" xmlns="http://www.w3.org/2000/svg"><rect width="50.0" height="50.0" x="0.0" y="0.0" fill="#00FF00" /></svg>'
        parser = SVGParser()
        scene = parser.parse(svg_content, "t", "e")
        
        self.assertEqual(len(scene.root.children), 1)
        self.assertIsInstance(scene.root.children[0], RectNode)
        self.assertEqual(scene.root.children[0].style.fill_color, "#00FF00")
        
        exporter = SVGExporter()
        out_svg = exporter.export(scene)
        
        # Check basic containment
        self.assertIn('<rect', out_svg)
        self.assertIn('fill="#00FF00"', out_svg)

    def test_image_layer_vector_integration(self):
        comp = ImageComposition(width=200, height=200, tenant_id="t", env="e")
        
        vscene = VectorScene(width=100, height=100, tenant_id="t", env="e")
        circle = CircleNode(radius=20, style=VectorStyle(fill_color="#0000FF"))
        vscene.root.children.append(circle)
        
        layer = ImageLayer(vector_scene=vscene, x=0, y=0)
        comp.layers.append(layer)
        
        png_bytes = self.backend.render(comp)
        img = Image.open(io.BytesIO(png_bytes))
        
        # Check blue pixel (circle at 0,0 means center is 0,0 usually? 
        # Wait, CircleNode usage in simple renderer:
        # cx = transform.x + radius, cy = ... 
        # By default transform.x=0. So cx=20, cy=20.
        # So pixel at 20,20 should be blue.
        
        self.assertEqual(img.getpixel((20,20)), (0, 0, 255, 255))

    def test_render_with_transform(self):
        scene = VectorScene(width=120, height=120, tenant_id="t", env="e")
        rect = RectNode(width=40, height=20, style=VectorStyle(fill_color="#FF00FF"))
        rect.transform.rotation = 45
        rect.transform.x = 40
        rect.transform.y = 40
        scene.root.children.append(rect)

        img = self.renderer.render(scene)
        # Rotated rect should still draw some pixels outside original axis-aligned bounds.
        self.assertNotEqual(img.getpixel((40, 40)), (0, 0, 0, 0))

    def test_boolean_ops_meta_flag(self):
        scene = VectorScene(width=100, height=100, tenant_id="t", env="e")
        rect_a = RectNode(width=20, height=20)
        rect_a.id = "rect-a"
        rect_b = RectNode(width=20, height=20)
        rect_b.id = "rect-b"
        scene.root.children.extend([rect_a, rect_b])
        scene.boolean_ops.append(BooleanOperation(operation="union", operands=["rect-a", "rect-b"]))

        self.renderer.render(scene)
        self.assertIn(scene.meta.get("boolean_ops"), {"NOT_IMPLEMENTED", "APPLIED"})

    def test_service_includes_layout_hash_meta(self):
        mock_media = MagicMock()
        mock_media.register_upload.return_value = MediaAsset(id="asset123", tenant_id="t", env="e", kind="image", source_uri="/tmp/v.png")
        mock_media.register_artifact.return_value = DerivedArtifact(id="art456", parent_asset_id="asset123", tenant_id="t", env="e", kind="image_render", uri="/tmp/v.png")

        service = VectorService(media_service=mock_media)
        scene = VectorScene(width=80, height=80, tenant_id="t", env="e")
        rect = RectNode(width=10, height=10)
        scene.root.children.append(rect)

        art_id = service.rasterize_scene_artifact(scene)

        self.assertEqual(art_id, "art456")
        artifact_req = mock_media.register_artifact.call_args[0][0]
        self.assertEqual(artifact_req.meta["layout_hash"], scene.compute_layout_hash())
        self.assertIn("boolean_ops", artifact_req.meta)

if __name__ == '__main__':
    unittest.main()
