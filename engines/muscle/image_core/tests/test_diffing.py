"""Tests for composition diffing and comparison."""

import unittest
from engines.image_core.diffing import (
    CompositionDiff, LayerDiff, DiffType, CompositionDiffer, DiffReport
)
from engines.image_core.models import ImageComposition, ImageLayer


class TestLayerDiff(unittest.TestCase):
    """Test LayerDiff model."""
    
    def test_layer_diff_creation(self):
        """Test creating a layer diff."""
        diff = LayerDiff(
            layer_id="layer-1",
            layer_name="Background",
            diff_type=DiffType.LAYER_REMOVED,
            description="Layer was removed"
        )
        
        self.assertEqual(diff.layer_id, "layer-1")
        self.assertEqual(diff.diff_type, DiffType.LAYER_REMOVED)
    
    def test_layer_property_change(self):
        """Test layer property change diff."""
        diff = LayerDiff(
            layer_id="layer-1",
            layer_name="Image",
            diff_type=DiffType.PROPERTY_CHANGED,
            property_name="opacity",
            old_value=0.8,
            new_value=1.0
        )
        
        self.assertEqual(diff.property_name, "opacity")
        self.assertEqual(diff.old_value, 0.8)
        self.assertEqual(diff.new_value, 1.0)


class TestCompositionDiff(unittest.TestCase):
    """Test CompositionDiff model."""
    
    def test_composition_diff_creation(self):
        """Test creating composition diff."""
        diff = CompositionDiff(
            width_a=1920,
            height_a=1080,
            width_b=1920,
            height_b=1080,
            background_color_a="#FFFFFF",
            background_color_b="#FFFFFF"
        )
        
        self.assertEqual(diff.width_a, 1920)
        self.assertEqual(diff.total_changes, 0)
        self.assertEqual(diff.similarity_score, 1.0)
    
    def test_add_layer_diff(self):
        """Test adding layer diff."""
        diff = CompositionDiff(
            width_a=1920, height_a=1080,
            width_b=1920, height_b=1080,
            background_color_a="#FFF", background_color_b="#FFF"
        )
        
        layer_diff = LayerDiff(
            layer_id="l1",
            layer_name="Layer 1",
            diff_type=DiffType.LAYER_ADDED
        )
        
        diff.add_layer_diff(layer_diff)
        
        self.assertEqual(len(diff.layer_diffs), 1)
        self.assertEqual(diff.total_changes, 1)
    
    def test_add_property_change(self):
        """Test adding property change."""
        diff = CompositionDiff(
            width_a=1920, height_a=1080,
            width_b=1920, height_b=1080,
            background_color_a="#FFF", background_color_b="#FFF"
        )
        
        diff.add_property_change("background_color", "#FFF", "#000")
        
        self.assertIn("background_color", diff.properties_changed)
        self.assertEqual(diff.total_changes, 1)
    
    def test_get_summary(self):
        """Test getting diff summary."""
        diff = CompositionDiff(
            width_a=1920, height_a=1080,
            width_b=1920, height_b=1080,
            background_color_a="#FFF", background_color_b="#FFF"
        )
        
        diff.add_layer_diff(LayerDiff(
            layer_id="l1", layer_name="L1",
            diff_type=DiffType.LAYER_ADDED
        ))
        diff.add_property_change("opacity", 0.5, 1.0)
        
        summary = diff.get_summary()
        
        self.assertEqual(summary["total_changes"], 2)
        self.assertEqual(summary["layers_added"], 1)


class TestCompositionDiffer(unittest.TestCase):
    """Test CompositionDiffer."""
    
    def setUp(self):
        """Create test compositions."""
        self.comp_a = ImageComposition(
            width=1920,
            height=1080,
            background_color="#FFFFFF",
            layers=[
                ImageLayer(
                    id="bg",
                    name="Background",
                    color="#FFFFFF",
                    x=0, y=0,
                    width=1920, height=1080
                ),
                ImageLayer(
                    id="text",
                    name="Title",
                    text="Hello",
                    x=100, y=100,
                    width=800, height=200
                ),
            ],
            tenant_id="test",
            env="test"
        )
        
        self.comp_b = ImageComposition(
            width=1920,
            height=1080,
            background_color="#FFFFFF",
            layers=[
                ImageLayer(
                    id="bg",
                    name="Background",
                    color="#F0F0F0",
                    x=0, y=0,
                    width=1920, height=1080
                ),
                ImageLayer(
                    id="text",
                    name="Title",
                    text="Hello World",
                    x=100, y=100,
                    width=800, height=200
                ),
            ],
            tenant_id="test",
            env="test"
        )
    
    def test_identical_compositions(self):
        """Test comparing identical compositions."""
        diff = CompositionDiffer.compare_compositions(self.comp_a, self.comp_a)
        
        self.assertEqual(diff.total_changes, 0)
        self.assertEqual(diff.similarity_score, 1.0)
    
    def test_layer_color_change(self):
        """Test detecting layer color change."""
        diff = CompositionDiffer.compare_compositions(self.comp_a, self.comp_b)
        
        # Should detect layer modification
        layer_diffs = [d for d in diff.layer_diffs if d.diff_type == DiffType.LAYER_MODIFIED]
        self.assertGreater(len(layer_diffs), 0)
    
    def test_dimension_change(self):
        """Test detecting dimension change."""
        comp_wide = ImageComposition(
            width=2560,
            height=1440,
            background_color="#FFFFFF",
            layers=[],
            tenant_id="test",
            env="test"
        )
        
        diff = CompositionDiffer.compare_compositions(self.comp_a, comp_wide)
        
        # Should detect dimension change
        self.assertIn("dimensions", diff.properties_changed)
        self.assertGreater(diff.total_changes, 0)
    
    def test_background_color_change(self):
        """Test detecting background color change."""
        comp_dark = ImageComposition(
            width=1920,
            height=1080,
            background_color="#000000",
            layers=[],
            tenant_id="test",
            env="test"
        )
        
        diff = CompositionDiffer.compare_compositions(self.comp_a, comp_dark)
        
        self.assertIn("background_color", diff.properties_changed)
        self.assertEqual(diff.properties_changed["background_color"][0], "#FFFFFF")
        self.assertEqual(diff.properties_changed["background_color"][1], "#000000")
    
    def test_layer_added(self):
        """Test detecting added layer."""
        comp_with_extra = ImageComposition(
            width=1920,
            height=1080,
            background_color="#FFFFFF",
            layers=self.comp_a.layers + [
                ImageLayer(id="extra", name="Extra Layer", color="#FF0000", x=0, y=0, width=100, height=100)
            ],
            tenant_id="test",
            env="test"
        )
        
        diff = CompositionDiffer.compare_compositions(self.comp_a, comp_with_extra)
        
        # Should detect added layer
        added = [d for d in diff.layer_diffs if d.diff_type == DiffType.LAYER_ADDED]
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0].layer_id, "extra")
    
    def test_layer_removed(self):
        """Test detecting removed layer."""
        comp_minimal = ImageComposition(
            width=1920,
            height=1080,
            background_color="#FFFFFF",
            layers=[self.comp_a.layers[0]],  # Only background
            tenant_id="test",
            env="test"
        )
        
        diff = CompositionDiffer.compare_compositions(self.comp_a, comp_minimal)
        
        # Should detect removed layer
        removed = [d for d in diff.layer_diffs if d.diff_type == DiffType.LAYER_REMOVED]
        self.assertEqual(len(removed), 1)
        self.assertEqual(removed[0].layer_id, "text")
    
    def test_similarity_score_calculation(self):
        """Test similarity score calculation."""
        # Identical compositions
        diff_identical = CompositionDiffer.compare_compositions(self.comp_a, self.comp_a)
        self.assertEqual(diff_identical.similarity_score, 1.0)
        
        # Compositions with changes
        comp_modified = ImageComposition(
            width=2560,  # Different width
            height=1440,  # Different height
            background_color="#000000",  # Different color
            layers=[],
            tenant_id="test",
            env="test"
        )
        
        diff_modified = CompositionDiffer.compare_compositions(self.comp_a, comp_modified)
        self.assertLess(diff_modified.similarity_score, 1.0)
        self.assertGreater(diff_modified.similarity_score, 0.0)
    
    def test_pixel_hash_comparison(self):
        """Test comparing render hashes."""
        hash_a = "abc123def456"
        hash_b = "abc123def456"
        
        result = CompositionDiffer.compare_pixel_hashes(hash_a, hash_b)
        
        self.assertTrue(result["hashes_match"])
        self.assertTrue(result["content_identical"])
        self.assertEqual(result["similarity"], 1.0)
    
    def test_pixel_hash_difference(self):
        """Test when render hashes differ."""
        hash_a = "abc123def456"
        hash_b = "xyz789ijk012"
        
        result = CompositionDiffer.compare_pixel_hashes(hash_a, hash_b)
        
        self.assertFalse(result["hashes_match"])
        self.assertFalse(result["content_identical"])
        self.assertEqual(result["similarity"], 0.0)
    
    def test_dimension_comparison(self):
        """Test comparing artifact dimensions."""
        result = CompositionDiffer.compare_artifact_dimensions(
            1920, 1080,
            2560, 1440
        )
        
        self.assertEqual(result["width_change"], 640)
        self.assertEqual(result["height_change"], 360)
        self.assertFalse(result["dimensions_match"])
    
    def test_dimension_percentage_change(self):
        """Test dimension change percentage calculation."""
        result = CompositionDiffer.compare_artifact_dimensions(
            1000, 1000,
            1200, 800
        )
        
        self.assertAlmostEqual(result["width_change_pct"], 20.0, places=1)
        self.assertAlmostEqual(result["height_change_pct"], -20.0, places=1)


class TestDiffReport(unittest.TestCase):
    """Test DiffReport for presentation."""
    
    def test_report_creation(self):
        """Test creating a diff report."""
        diff = CompositionDiff(
            width_a=1920, height_a=1080,
            width_b=1920, height_b=1080,
            background_color_a="#FFF", background_color_b="#000"
        )
        diff.add_property_change("background_color", "#FFF", "#000")
        
        report = DiffReport(
            title="Composition Comparison",
            comparison_a="Version 1",
            comparison_b="Version 2",
            timestamp="2025-12-21T10:00:00Z",
            diff=diff
        )
        
        self.assertEqual(report.title, "Composition Comparison")
        self.assertIsNotNone(report.diff)
    
    def test_report_markdown_generation(self):
        """Test generating markdown report."""
        diff = CompositionDiff(
            width_a=1920, height_a=1080,
            width_b=2560, height_b=1440,
            background_color_a="#FFF", background_color_b="#FFF"
        )
        diff.add_property_change("dimensions", "1920x1080", "2560x1440")
        
        report = DiffReport(
            title="Test Diff",
            comparison_a="A",
            comparison_b="B",
            timestamp="2025-12-21",
            diff=diff
        )
        
        markdown = report.to_markdown()
        
        self.assertIn("# Test Diff", markdown)
        self.assertIn("Total Changes", markdown)
        self.assertIn("Dimension Changes", markdown)
    
    def test_report_json_conversion(self):
        """Test converting report to JSON."""
        diff = CompositionDiff(
            width_a=1920, height_a=1080,
            width_b=1920, height_b=1080,
            background_color_a="#FFF", background_color_b="#FFF"
        )
        
        report = DiffReport(
            title="Test",
            comparison_a="A",
            comparison_b="B",
            timestamp="2025-12-21",
            diff=diff
        )
        
        json_data = report.to_json()
        
        self.assertIn("title", json_data)
        self.assertIn("diff", json_data)
        self.assertEqual(json_data["title"], "Test")


class TestDifferEdgeCases(unittest.TestCase):
    """Test edge cases in diffing."""
    
    def test_empty_compositions(self):
        """Test comparing empty compositions."""
        comp_a = ImageComposition(
            width=1920, height=1080,
            background_color="#FFF",
            layers=[],
            tenant_id="test",
            env="test"
        )
        
        comp_b = ImageComposition(
            width=1920, height=1080,
            background_color="#FFF",
            layers=[],
            tenant_id="test",
            env="test"
        )
        
        diff = CompositionDiffer.compare_compositions(comp_a, comp_b)
        
        self.assertEqual(diff.total_changes, 0)
        self.assertEqual(diff.similarity_score, 1.0)
    
    def test_composition_with_many_layers(self):
        """Test comparing compositions with many layers."""
        layers = [
            ImageLayer(id=f"l{i}", name=f"Layer {i}", color=f"#{i:06X}",
                      x=i*10, y=i*10, width=100, height=100)
            for i in range(10)
        ]
        
        comp_a = ImageComposition(
            width=1920, height=1080,
            background_color="#FFF",
            layers=layers,
            tenant_id="test",
            env="test"
        )
        
        # Remove one layer
        comp_b = ImageComposition(
            width=1920, height=1080,
            background_color="#FFF",
            layers=layers[:-1],
            tenant_id="test",
            env="test"
        )
        
        diff = CompositionDiffer.compare_compositions(comp_a, comp_b)
        
        # Should detect one removed layer
        removed = [d for d in diff.layer_diffs if d.diff_type == DiffType.LAYER_REMOVED]
        self.assertEqual(len(removed), 1)


if __name__ == "__main__":
    unittest.main()
