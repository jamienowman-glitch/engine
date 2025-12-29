"""Tests for auto-crop intelligence."""

import unittest
from engines.image_core.auto_crop import (
    AutoCropEngine, FocalPoint, AspectRatioConfig, CropBox, AutoCropRequest
)
from engines.image_core.service import ImageCoreService
from engines.media_v2.service import MediaService, InMemoryMediaRepository, LocalMediaStorage


class TestAutoCropEngine(unittest.TestCase):
    """Test AutoCropEngine core functionality."""
    
    def test_calculate_crop_box_center_crop_wider_source(self):
        """Test crop when source is wider than target (crop width)."""
        # Source: 1920x1080 (16:9)
        # Target: 1:1 (square)
        crop_box = AutoCropEngine.calculate_crop_box(
            source_width=1920,
            source_height=1080,
            target_ratio=1.0  # 1:1 square
        )
        
        # Should crop width, keep height
        self.assertEqual(crop_box.height, 1080)
        self.assertEqual(crop_box.width, 1080)
        self.assertGreater(crop_box.x, 0)  # Centered horizontally
        self.assertEqual(crop_box.y, 0)  # Full height
    
    def test_calculate_crop_box_center_crop_taller_source(self):
        """Test crop when source is taller than target (crop height)."""
        # Source: 1080x1920 (portrait)
        # Target: 16:9 (landscape)
        crop_box = AutoCropEngine.calculate_crop_box(
            source_width=1080,
            source_height=1920,
            target_ratio=16/9
        )
        
        # Should crop height, keep width
        self.assertEqual(crop_box.width, 1080)
        self.assertLess(crop_box.height, 1920)
        self.assertEqual(crop_box.x, 0)  # Full width
        self.assertGreater(crop_box.y, 0)  # Centered vertically
    
    def test_calculate_crop_box_with_focal_point(self):
        """Test that focal point influences crop position."""
        source_w, source_h = 1920, 1080
        target_ratio = 1.0  # 1:1 square
        
        # Focal point on left side
        focal_left = FocalPoint(x=0.2, y=0.5)
        crop_left = AutoCropEngine.calculate_crop_box(
            source_width=source_w,
            source_height=source_h,
            target_ratio=target_ratio,
            focal_point=focal_left
        )
        
        # Focal point on right side
        focal_right = FocalPoint(x=0.8, y=0.5)
        crop_right = AutoCropEngine.calculate_crop_box(
            source_width=source_w,
            source_height=source_h,
            target_ratio=target_ratio,
            focal_point=focal_right
        )
        
        # Crops should be at different X positions
        self.assertNotEqual(crop_left.x, crop_right.x)
        self.assertLess(crop_left.x, crop_right.x)
    
    def test_aspect_ratio_config_parsing(self):
        """Test parsing aspect ratio strings."""
        config = AspectRatioConfig(aspect_ratio="16:9")
        self.assertAlmostEqual(config.get_ratio_value(), 16/9, places=2)
        
        config = AspectRatioConfig(aspect_ratio="1:1")
        self.assertAlmostEqual(config.get_ratio_value(), 1.0, places=2)
        
        config = AspectRatioConfig(aspect_ratio="4:3")
        self.assertAlmostEqual(config.get_ratio_value(), 4/3, places=2)
    
    def test_aspect_ratio_invalid_format(self):
        """Test that invalid aspect ratios raise errors."""
        with self.assertRaises(ValueError):
            AspectRatioConfig(aspect_ratio="16x9")  # Wrong separator
        
        with self.assertRaises(ValueError):
            AspectRatioConfig(aspect_ratio="0:9")  # Zero value
        
        with self.assertRaises(ValueError):
            AspectRatioConfig(aspect_ratio="abc:def")  # Non-numeric
    
    def test_crop_box_aspect_ratio_method(self):
        """Test CropBox aspect_ratio calculation."""
        crop = CropBox(x=0, y=0, width=1920, height=1080)
        self.assertAlmostEqual(crop.aspect_ratio(), 1920/1080, places=2)
        
        crop = CropBox(x=0, y=0, width=1080, height=1080)
        self.assertAlmostEqual(crop.aspect_ratio(), 1.0, places=2)
    
    def test_merge_focal_points(self):
        """Test merging multiple focal points into weighted average."""
        fp1 = FocalPoint(x=0.2, y=0.5, weight=1.0)
        fp2 = FocalPoint(x=0.8, y=0.5, weight=1.0)
        
        merged = AutoCropEngine.merge_focal_points([fp1, fp2])
        
        self.assertAlmostEqual(merged.x, 0.5, places=1)  # Centered X
        self.assertAlmostEqual(merged.y, 0.5, places=1)  # Centered Y
    
    def test_preset_ratios_defined(self):
        """Test that common presets are defined."""
        presets = AutoCropEngine.PRESET_RATIOS
        
        # Check social media presets
        self.assertIn("instagram-square", presets)
        self.assertIn("instagram-story", presets)
        self.assertIn("facebook-cover", presets)
        self.assertIn("twitter-header", presets)
        
        # Check web presets
        self.assertIn("widescreen", presets)
        self.assertIn("square", presets)
        self.assertIn("mobile", presets)
        
        # Check print presets
        self.assertIn("postcard", presets)
        self.assertIn("business-card", presets)
    
    def test_get_crop_for_preset(self):
        """Test getting crop box for named presets."""
        # Instagram square (1:1)
        crop = AutoCropEngine.get_crop_for_preset(
            preset_name="instagram-square",
            source_width=1920,
            source_height=1080
        )
        
        self.assertIsNotNone(crop)
        self.assertEqual(crop.width, crop.height)  # Should be square
        self.assertEqual(crop.height, 1080)  # Limited by source height
    
    def test_get_crop_for_invalid_preset(self):
        """Test that invalid presets return None."""
        crop = AutoCropEngine.get_crop_for_preset(
            preset_name="non-existent-preset",
            source_width=1920,
            source_height=1080
        )
        
        self.assertIsNone(crop)
    
    def test_crop_bounds_within_source(self):
        """Test that calculated crops never exceed source bounds."""
        source_w, source_h = 800, 600
        
        for aspect_ratio in [0.5, 1.0, 2.0, 3.0]:
            crop = AutoCropEngine.calculate_crop_box(
                source_width=source_w,
                source_height=source_h,
                target_ratio=aspect_ratio
            )
            
            # Crop must be within bounds
            self.assertGreaterEqual(crop.x, 0)
            self.assertGreaterEqual(crop.y, 0)
            self.assertLessEqual(crop.x + crop.width, source_w)
            self.assertLessEqual(crop.y + crop.height, source_h)
    
    def test_focal_point_at_edge(self):
        """Test focal point handling at image edges."""
        source_w, source_h = 1920, 1080
        target_ratio = 1.0  # 1:1 square
        
        # Focal point at top-left corner
        focal_corner = FocalPoint(x=0.0, y=0.0)
        crop = AutoCropEngine.calculate_crop_box(
            source_width=source_w,
            source_height=source_h,
            target_ratio=target_ratio,
            focal_point=focal_corner
        )
        
        # Should still produce valid crop within bounds
        self.assertGreaterEqual(crop.x, 0)
        self.assertGreaterEqual(crop.y, 0)
        self.assertLessEqual(crop.x + crop.width, source_w)
        self.assertLessEqual(crop.y + crop.height, source_h)


class TestAutoCropService(unittest.TestCase):
    """Test ImageCoreService auto-crop methods."""
    
    def setUp(self):
        """Initialize service."""
        repo = InMemoryMediaRepository()
        storage = LocalMediaStorage()
        media_svc = MediaService(repo=repo, storage=storage)
        self.service = ImageCoreService(media_service=media_svc)
    
    def test_calculate_auto_crop_basic(self):
        """Test service calculate_auto_crop method."""
        result = self.service.calculate_auto_crop(
            source_width=1920,
            source_height=1080,
            aspect_ratio="1:1"
        )
        
        self.assertIn("crop_box", result)
        self.assertIn("confidence", result)
        self.assertIn("method", result)
        
        crop = result["crop_box"]
        self.assertEqual(crop["width"], crop["height"])
    
    def test_calculate_auto_crop_with_focal_point(self):
        """Test auto-crop with focal point."""
        result = self.service.calculate_auto_crop(
            source_width=1920,
            source_height=1080,
            aspect_ratio="16:9",
            focal_point=(0.3, 0.7)
        )
        
        self.assertEqual(result["method"], "focal_point")
        self.assertEqual(result["focal_point_used"], (0.3, 0.7))
        self.assertGreater(result["confidence"], 0.75)
    
    def test_calculate_auto_crop_invalid_ratio(self):
        """Test error handling for invalid aspect ratio."""
        with self.assertRaises(ValueError):
            self.service.calculate_auto_crop(
                source_width=1920,
                source_height=1080,
                aspect_ratio="invalid"
            )
    
    def test_get_crop_for_preset_valid(self):
        """Test get_crop_for_preset with valid preset."""
        result = self.service.get_crop_for_preset(
            preset_name="instagram-square",
            source_width=1920,
            source_height=1080
        )
        
        self.assertIsNotNone(result)
        self.assertIn("crop_box", result)
        self.assertEqual(result["preset"], "instagram-square")
        
        crop = result["crop_box"]
        self.assertEqual(crop["width"], crop["height"])
    
    def test_get_crop_for_preset_invalid(self):
        """Test get_crop_for_preset with invalid preset."""
        result = self.service.get_crop_for_preset(
            preset_name="non-existent",
            source_width=1920,
            source_height=1080
        )
        
        self.assertIsNone(result)
    
    def test_multiple_presets_crops_different(self):
        """Test that different presets produce different crops."""
        source_w, source_h = 2000, 2000  # Square source
        
        crops = {}
        for preset in ["instagram-square", "facebook-cover", "twitter-header", "youtube-thumbnail"]:
            result = self.service.get_crop_for_preset(
                preset_name=preset,
                source_width=source_w,
                source_height=source_h
            )
            if result:
                crops[preset] = result["crop_box"]
        
        # Different presets should produce different crop dimensions
        crop_shapes = {name: (crop["width"], crop["height"]) for name, crop in crops.items()}
        unique_shapes = len(set(crop_shapes.values()))
        
        # Should have at least 2 different crop shapes (not all same)
        self.assertGreater(unique_shapes, 1, "Different presets should produce different crop shapes")


if __name__ == "__main__":
    unittest.main()
