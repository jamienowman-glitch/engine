"""Tests for color extraction and palette generation."""

import unittest
from engines.image_core.color_extraction import (
    ColorExtractor, ColorMetrics, ColorPalette, ColorVariation, AccessibilityReport
)
from engines.image_core.models import ImageComposition, ImageLayer


class TestColorConversion(unittest.TestCase):
    """Test color format conversions."""
    
    def test_hex_to_rgb(self):
        """Test hex to RGB conversion."""
        rgb = ColorExtractor.hex_to_rgb("#FF0000")
        self.assertEqual(rgb, (255, 0, 0))
        
        rgb = ColorExtractor.hex_to_rgb("#00FF00")
        self.assertEqual(rgb, (0, 255, 0))
        
        rgb = ColorExtractor.hex_to_rgb("#0000FF")
        self.assertEqual(rgb, (0, 0, 255))
    
    def test_rgb_to_hex(self):
        """Test RGB to hex conversion."""
        hex_color = ColorExtractor.rgb_to_hex(255, 0, 0)
        self.assertEqual(hex_color, "#FF0000")
        
        hex_color = ColorExtractor.rgb_to_hex(0, 255, 0)
        self.assertEqual(hex_color, "#00FF00")
    
    def test_rgb_to_hsl(self):
        """Test RGB to HSL conversion."""
        hsl = ColorExtractor.rgb_to_hsl(255, 0, 0)  # Red
        self.assertEqual(hsl[0], 0)  # Hue at 0
        self.assertEqual(hsl[1], 100)  # Full saturation
        
        hsl = ColorExtractor.rgb_to_hsl(128, 128, 128)  # Gray
        self.assertEqual(hsl[1], 0)  # No saturation
    
    def test_rgb_to_hsv(self):
        """Test RGB to HSV conversion."""
        hsv = ColorExtractor.rgb_to_hsv(255, 0, 0)  # Red
        self.assertEqual(hsv[0], 0)  # Hue at 0
        self.assertEqual(hsv[1], 100)  # Full saturation
        self.assertEqual(hsv[2], 100)  # Full value
    
    def test_hsl_to_rgb(self):
        """Test HSL to RGB conversion."""
        rgb = ColorExtractor.hsl_to_rgb(0, 100, 50)  # Red
        self.assertEqual(rgb[0], 255)
        self.assertEqual(rgb[1], 0)
        self.assertEqual(rgb[2], 0)
        
        rgb = ColorExtractor.hsl_to_rgb(120, 100, 50)  # Green
        self.assertEqual(rgb[0], 0)
        self.assertEqual(rgb[1], 255)
        self.assertEqual(rgb[2], 0)


class TestColorMetrics(unittest.TestCase):
    """Test color metrics creation."""
    
    def test_create_color_metrics(self):
        """Test creating color metrics."""
        metrics = ColorExtractor.create_color_metrics("#FF0000")
        
        self.assertEqual(metrics.hex_value, "#FF0000")
        self.assertEqual(metrics.rgb, (255, 0, 0))
        self.assertEqual(metrics.hsl[0], 0)  # Hue
        self.assertEqual(metrics.frequency, 1)
    
    def test_luminance_calculation(self):
        """Test luminance calculation for WCAG."""
        # White should have high luminance
        luminance_white = ColorExtractor.calculate_luminance(255, 255, 255)
        self.assertGreater(luminance_white, 0.9)
        
        # Black should have low luminance
        luminance_black = ColorExtractor.calculate_luminance(0, 0, 0)
        self.assertLess(luminance_black, 0.1)
        
        # White should be brighter than black
        self.assertGreater(luminance_white, luminance_black)
    
    def test_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = ColorExtractor.create_color_metrics("#FF0000")
        data = metrics.to_dict()
        
        self.assertIn("hex", data)
        self.assertIn("rgb", data)
        self.assertIn("hsl", data)
        self.assertIn("luminance", data)
        self.assertEqual(data["hex"], "#FF0000")


class TestColorPalette(unittest.TestCase):
    """Test color palette operations."""
    
    def test_palette_creation(self):
        """Test creating color palette."""
        primary = ColorExtractor.create_color_metrics("#FF0000")
        secondary = ColorExtractor.create_color_metrics("#00FF00")
        
        palette = ColorPalette(
            primary=primary,
            secondary=secondary,
            colors=[primary, secondary]
        )
        
        self.assertEqual(palette.primary.hex_value, "#FF0000")
        self.assertEqual(palette.secondary.hex_value, "#00FF00")
    
    def test_get_dominant_colors(self):
        """Test getting dominant colors."""
        color1 = ColorExtractor.create_color_metrics("#FF0000", frequency=5)
        color2 = ColorExtractor.create_color_metrics("#00FF00", frequency=3)
        color3 = ColorExtractor.create_color_metrics("#0000FF", frequency=1)
        
        palette = ColorPalette(
            primary=color1,
            colors=[color1, color2, color3]
        )
        
        dominant = palette.get_dominant_colors(2)
        
        self.assertEqual(len(dominant), 2)
        self.assertEqual(dominant[0].frequency, 5)
        self.assertEqual(dominant[1].frequency, 3)
    
    def test_palette_to_dict(self):
        """Test converting palette to dictionary."""
        primary = ColorExtractor.create_color_metrics("#FF0000")
        palette = ColorPalette(primary=primary)
        data = palette.to_dict()
        
        self.assertIn("primary", data)
        self.assertIn("all_colors", data)
        self.assertIn("extracted_at", data)


class TestColorExtraction(unittest.TestCase):
    """Test color extraction from compositions."""
    
    def test_extract_from_empty_composition(self):
        """Test extracting colors from empty composition."""
        comp = ImageComposition(
            width=1920, height=1080,
            background_color="#FFFFFF",
            layers=[],
            tenant_id="test",
            env="test"
        )
        
        palette = ColorExtractor.extract_from_composition(comp)
        
        self.assertIsNotNone(palette.primary)
        self.assertEqual(palette.background_color, "#FFFFFF")
    
    def test_extract_from_composition_with_layers(self):
        """Test extracting colors from composition with colored layers."""
        comp = ImageComposition(
            width=1920, height=1080,
            background_color="#FFFFFF",
            layers=[
                ImageLayer(
                    id="bg", name="Background",
                    color="#FF0000",  # Red
                    x=0, y=0, width=1920, height=1080
                ),
                ImageLayer(
                    id="text", name="Text",
                    color="#000000",  # Black
                    x=100, y=100, width=800, height=200
                ),
            ],
            tenant_id="test",
            env="test"
        )
        
        palette = ColorExtractor.extract_from_composition(comp)
        
        self.assertIsNotNone(palette.primary)
        self.assertGreater(len(palette.colors), 0)
    
    def test_color_frequency_tracking(self):
        """Test that repeated colors are tracked."""
        comp = ImageComposition(
            width=1920, height=1080,
            background_color="#FFFFFF",
            layers=[
                ImageLayer(id="l1", name="L1", color="#FF0000", x=0, y=0, width=100, height=100),
                ImageLayer(id="l2", name="L2", color="#FF0000", x=100, y=0, width=100, height=100),
                ImageLayer(id="l3", name="L3", color="#00FF00", x=200, y=0, width=100, height=100),
            ],
            tenant_id="test",
            env="test"
        )
        
        palette = ColorExtractor.extract_from_composition(comp)
        
        # Find red color in palette
        red_color = next((c for c in palette.colors if c.hex_value == "#FF0000"), None)
        self.assertIsNotNone(red_color)
        self.assertEqual(red_color.frequency, 2)


class TestPaletteGeneration(unittest.TestCase):
    """Test palette generation."""
    
    def test_generate_palette_sizes(self):
        """Test generating palettes of different sizes."""
        colors = [
            ColorExtractor.create_color_metrics("#FF0000", frequency=10),
            ColorExtractor.create_color_metrics("#00FF00", frequency=8),
            ColorExtractor.create_color_metrics("#0000FF", frequency=6),
            ColorExtractor.create_color_metrics("#FFFF00", frequency=4),
            ColorExtractor.create_color_metrics("#FF00FF", frequency=2),
        ]
        
        palettes = ColorExtractor.generate_palette_sizes(colors, sizes=[3, 5])
        
        self.assertEqual(len(palettes[3]), 3)
        self.assertEqual(len(palettes[5]), 5)
        self.assertEqual(palettes[5][0], "#FF0000")  # Highest frequency first


class TestColorVariations(unittest.TestCase):
    """Test color variation generation."""
    
    def test_generate_variations(self):
        """Test generating color variations."""
        variations = ColorExtractor.generate_variations("#FF0000")
        
        self.assertGreater(len(variations), 0)
        
        # Check that variations are different
        hex_colors = [v.result_color for v in variations]
        self.assertGreater(len(set(hex_colors)), 1)
    
    def test_lightness_adjustment(self):
        """Test lightness adjustment."""
        variations = ColorExtractor.generate_variations(
            "#FF0000",
            variations=[
                {"lightness_adjust": 20},  # Lighter red
                {"lightness_adjust": -20},  # Darker red
            ]
        )
        
        self.assertEqual(len(variations), 2)
        
        # Lighter should have higher lightness
        rgb_light = ColorExtractor.hex_to_rgb(variations[0].result_color)
        rgb_dark = ColorExtractor.hex_to_rgb(variations[1].result_color)
        
        lum_light = ColorExtractor.calculate_luminance(*rgb_light)
        lum_dark = ColorExtractor.calculate_luminance(*rgb_dark)
        
        self.assertGreater(lum_light, lum_dark)
    
    def test_saturation_adjustment(self):
        """Test saturation adjustment."""
        variations = ColorExtractor.generate_variations(
            "#FF0000",
            variations=[
                {"saturation_adjust": 30},  # More saturated
                {"saturation_adjust": -30},  # Less saturated
            ]
        )
        
        self.assertEqual(len(variations), 2)
        
        # More saturated should have higher saturation
        hsl1 = ColorExtractor.rgb_to_hsl(*ColorExtractor.hex_to_rgb(variations[0].result_color))
        hsl2 = ColorExtractor.rgb_to_hsl(*ColorExtractor.hex_to_rgb(variations[1].result_color))
        
        self.assertGreater(hsl1[1], hsl2[1])
    
    def test_hue_shift(self):
        """Test hue shift."""
        variations = ColorExtractor.generate_variations(
            "#FF0000",
            variations=[
                {"hue_shift": 60},  # +60 hue
                {"hue_shift": -60},  # -60 hue
            ]
        )
        
        # Should produce different colors
        self.assertNotEqual(variations[0].result_color, variations[1].result_color)


class TestWCAGContrast(unittest.TestCase):
    """Test WCAG contrast compliance checking."""
    
    def test_white_on_black(self):
        """Test white text on black background."""
        report = ColorExtractor.check_contrast_wcag("#FFFFFF", "#000000")
        
        self.assertGreater(report.contrast_ratio, 20)
        self.assertTrue(report.wcag_aa_compliant)
        self.assertTrue(report.wcag_aaa_compliant)
    
    def test_poor_contrast(self):
        """Test poor contrast."""
        report = ColorExtractor.check_contrast_wcag("#FFFF00", "#FFFFFF")  # Yellow on white
        
        self.assertLess(report.contrast_ratio, 2.0)
        self.assertFalse(report.wcag_aa_compliant)
        self.assertFalse(report.wcag_aaa_compliant)
    
    def test_large_text_compliance(self):
        """Test large text compliance (lower threshold)."""
        # Color pair that passes large text but not normal text
        report = ColorExtractor.check_contrast_wcag("#999999", "#000000")  # Gray on black
        
        # Should pass large text AA
        self.assertTrue(report.wcag_large_text_aa)
    
    def test_contrast_to_dict(self):
        """Test converting contrast report to dict."""
        report = ColorExtractor.check_contrast_wcag("#FFFFFF", "#000000")
        data = report.to_dict()
        
        self.assertIn("contrast_ratio", data)
        self.assertIn("wcag_aa_compliant", data)
        self.assertIn("wcag_aaa_compliant", data)


class TestAccessibleContrast(unittest.TestCase):
    """Test finding accessible color variations."""
    
    def test_find_accessible_contrast(self):
        """Test finding variation with accessible contrast."""
        # Yellow on white - poor contrast
        # Should find darker yellow or lightened white won't help
        result = ColorExtractor.find_accessible_contrast(
            "#FFFF00", "#FFFFFF", target_ratio=4.5
        )
        
        # Should find a darker yellow that works
        if result:
            self.assertNotEqual(result, "#FFFF00")
            report = ColorExtractor.check_contrast_wcag(result, "#FFFFFF")
            self.assertGreaterEqual(report.contrast_ratio, 4.5)


class TestColorVariationModel(unittest.TestCase):
    """Test ColorVariation model."""
    
    def test_variation_to_dict(self):
        """Test converting variation to dictionary."""
        variation = ColorVariation(
            base_color="#FF0000",
            lightness_adjust=20,
            result_color="#FF6666"
        )
        
        data = variation.to_dict()
        
        self.assertEqual(data["base_color"], "#FF0000")
        self.assertEqual(data["lightness_adjust"], 20)
        self.assertEqual(data["result_color"], "#FF6666")


if __name__ == "__main__":
    unittest.main()
