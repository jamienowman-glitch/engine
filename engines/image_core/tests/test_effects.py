"""Tests for layer effects system."""

import unittest
from engines.image_core.effects import (
    ShadowEffect, GlowEffect, BlurEffect, HighlightEffect, VignetteEffect,
    OpacityEffect, InvertEffect, SepiaEffect, GrayscaleEffect,
    LayerEffect, EffectStack, EffectEngine, EFFECT_PRESETS
)


class TestEffectModels(unittest.TestCase):
    """Test effect model validation and creation."""
    
    def test_shadow_effect_creation(self):
        """Test creating a shadow effect."""
        shadow = ShadowEffect(
            mode="drop",
            x_offset=2,
            y_offset=4,
            blur_radius=8,
            color="#000000",
            opacity=0.5
        )
        
        self.assertEqual(shadow.mode, "drop")
        self.assertEqual(shadow.x_offset, 2)
        self.assertEqual(shadow.opacity, 0.5)
    
    def test_shadow_effect_validation(self):
        """Test shadow effect field validation."""
        # Invalid offset (out of range)
        with self.assertRaises(ValueError):
            ShadowEffect(x_offset=200)  # Max is 100
        
        # Invalid opacity
        with self.assertRaises(ValueError):
            ShadowEffect(opacity=1.5)  # Max is 1.0
    
    def test_glow_effect_creation(self):
        """Test creating glow effect."""
        glow = GlowEffect(
            mode="outer",
            blur_radius=15,
            color="#FFFFFF",
            opacity=0.8
        )
        
        self.assertEqual(glow.mode, "outer")
        self.assertEqual(glow.blur_radius, 15)
    
    def test_blur_effect_creation(self):
        """Test creating blur effect."""
        blur = BlurEffect(
            mode="gaussian",
            radius=5,
            angle=0
        )
        
        self.assertEqual(blur.mode, "gaussian")
        self.assertEqual(blur.radius, 5)
    
    def test_vignette_effect_creation(self):
        """Test creating vignette effect."""
        vignette = VignetteEffect(
            darkness=0.6,
            radius=0.7,
            smoothness=0.5
        )
        
        self.assertEqual(vignette.darkness, 0.6)
        self.assertGreaterEqual(vignette.radius, 0.1)
    
    def test_opacity_effect_creation(self):
        """Test creating opacity effect."""
        opacity = OpacityEffect(value=0.75)
        
        self.assertEqual(opacity.value, 0.75)
    
    def test_grayscale_effect_creation(self):
        """Test creating grayscale effect."""
        gray = GrayscaleEffect(amount=1.0)
        
        self.assertEqual(gray.amount, 1.0)
    
    def test_sepia_effect_creation(self):
        """Test creating sepia effect."""
        sepia = SepiaEffect(amount=0.6)
        
        self.assertEqual(sepia.amount, 0.6)
    
    def test_invert_effect_creation(self):
        """Test creating invert effect."""
        invert = InvertEffect(amount=0.5)
        
        self.assertEqual(invert.amount, 0.5)


class TestLayerEffect(unittest.TestCase):
    """Test LayerEffect wrapper."""
    
    def test_layer_effect_creation(self):
        """Test creating a layer effect."""
        shadow = ShadowEffect(x_offset=2, y_offset=2)
        effect = LayerEffect(effect_config=shadow, order=0)
        
        self.assertIsNotNone(effect.effect_id)
        self.assertTrue(effect.enabled)
        self.assertEqual(effect.order, 0)
    
    def test_layer_effect_id_unique(self):
        """Test that effect IDs are unique."""
        shadow = ShadowEffect()
        effect1 = LayerEffect(effect_config=shadow)
        effect2 = LayerEffect(effect_config=shadow)
        
        self.assertNotEqual(effect1.effect_id, effect2.effect_id)


class TestEffectStack(unittest.TestCase):
    """Test EffectStack for managing multiple effects."""
    
    def test_effect_stack_add_effect(self):
        """Test adding effects to stack."""
        stack = EffectStack()
        
        shadow = ShadowEffect()
        effect = LayerEffect(effect_config=shadow, order=0)
        
        stack.add_effect(effect)
        
        self.assertEqual(len(stack.effects), 1)
    
    def test_effect_stack_sort_by_order(self):
        """Test that effects are sorted by order."""
        stack = EffectStack()
        
        # Add effects out of order
        shadow = ShadowEffect()
        glow = GlowEffect()
        blur = BlurEffect()
        
        effect_shadow = LayerEffect(effect_config=shadow, order=2)
        effect_glow = LayerEffect(effect_config=glow, order=0)
        effect_blur = LayerEffect(effect_config=blur, order=1)
        
        stack.add_effect(effect_shadow)
        stack.add_effect(effect_glow)
        stack.add_effect(effect_blur)
        
        # Should be sorted by order
        self.assertEqual(stack.effects[0].order, 0)
        self.assertEqual(stack.effects[1].order, 1)
        self.assertEqual(stack.effects[2].order, 2)
    
    def test_effect_stack_remove_effect(self):
        """Test removing effect from stack."""
        stack = EffectStack()
        
        shadow = ShadowEffect()
        effect = LayerEffect(effect_config=shadow)
        
        stack.add_effect(effect)
        self.assertEqual(len(stack.effects), 1)
        
        removed = stack.remove_effect(effect.effect_id)
        self.assertTrue(removed)
        self.assertEqual(len(stack.effects), 0)
    
    def test_effect_stack_remove_nonexistent(self):
        """Test removing non-existent effect."""
        stack = EffectStack()
        
        removed = stack.remove_effect("nonexistent-id")
        self.assertFalse(removed)
    
    def test_effect_stack_get_enabled_effects(self):
        """Test getting only enabled effects."""
        stack = EffectStack()
        
        shadow = ShadowEffect()
        glow = GlowEffect()
        
        effect1 = LayerEffect(effect_config=shadow, enabled=True)
        effect2 = LayerEffect(effect_config=glow, enabled=False)
        
        stack.add_effect(effect1)
        stack.add_effect(effect2)
        
        enabled = stack.get_enabled_effects()
        self.assertEqual(len(enabled), 1)
        self.assertEqual(enabled[0].effect_id, effect1.effect_id)


class TestEffectPresets(unittest.TestCase):
    """Test effect presets."""
    
    def test_presets_defined(self):
        """Test that effect presets are defined."""
        self.assertGreater(len(EFFECT_PRESETS), 0)
    
    def test_soft_shadow_preset(self):
        """Test soft shadow preset."""
        preset = EFFECT_PRESETS.get("soft-shadow")
        
        self.assertIsNotNone(preset)
        self.assertEqual(preset.name, "soft-shadow")
        self.assertEqual(len(preset.effects), 1)
        self.assertEqual(preset.effects[0].type, "shadow")
    
    def test_neon_glow_preset(self):
        """Test neon glow preset."""
        preset = EFFECT_PRESETS.get("neon-glow")
        
        self.assertIsNotNone(preset)
        self.assertEqual(len(preset.effects), 1)
        self.assertEqual(preset.effects[0].type, "glow")
    
    def test_vintage_preset(self):
        """Test vintage preset (multi-effect)."""
        preset = EFFECT_PRESETS.get("vintage")
        
        self.assertIsNotNone(preset)
        self.assertEqual(len(preset.effects), 2)  # Sepia + Vignette
    
    def test_grayscale_dramatic_preset(self):
        """Test grayscale dramatic preset."""
        preset = EFFECT_PRESETS.get("grayscale-dramatic")
        
        self.assertIsNotNone(preset)
        self.assertEqual(len(preset.effects), 2)  # Grayscale + Vignette
    
    def test_all_presets_have_description(self):
        """Test that all presets have descriptions."""
        for name, preset in EFFECT_PRESETS.items():
            self.assertIsNotNone(preset.description)
            self.assertIsInstance(preset.description, str)


class TestEffectEngine(unittest.TestCase):
    """Test EffectEngine functionality."""
    
    def test_get_preset(self):
        """Test getting preset by name."""
        preset = EffectEngine.get_preset("soft-shadow")
        
        self.assertIsNotNone(preset)
        self.assertEqual(preset.name, "soft-shadow")
    
    def test_get_nonexistent_preset(self):
        """Test getting non-existent preset."""
        preset = EffectEngine.get_preset("nonexistent")
        
        self.assertIsNone(preset)
    
    def test_list_presets(self):
        """Test listing all presets."""
        presets = EffectEngine.list_presets()
        
        self.assertIsInstance(presets, dict)
        self.assertGreater(len(presets), 0)
        
        # Check structure
        for name, info in presets.items():
            self.assertIn("description", info)
            self.assertIn("effects", info)
            self.assertIsInstance(info["effects"], list)
    
    def test_effect_engine_preset_in_list(self):
        """Test that all EFFECT_PRESETS are in list_presets."""
        presets_list = EffectEngine.list_presets()
        
        for preset_name in EFFECT_PRESETS.keys():
            self.assertIn(preset_name, presets_list)
    
    def test_apply_effect_stack_empty(self):
        """Test applying empty effect stack (should return original)."""
        stack = EffectStack()
        
        # Use empty bytes as test input
        result = EffectEngine.apply_effect_stack(b"test", stack)
        
        # Should return bytes (or original empty)
        self.assertIsInstance(result, bytes)


class TestEffectCombinations(unittest.TestCase):
    """Test various effect combinations."""
    
    def test_shadow_plus_glow_stack(self):
        """Test stacking shadow and glow effects."""
        stack = EffectStack()
        
        shadow = ShadowEffect()
        glow = GlowEffect()
        
        effect_shadow = LayerEffect(effect_config=shadow, order=0)
        effect_glow = LayerEffect(effect_config=glow, order=1)
        
        stack.add_effect(effect_shadow)
        stack.add_effect(effect_glow)
        
        self.assertEqual(len(stack.get_enabled_effects()), 2)
    
    def test_blur_with_opacity_stack(self):
        """Test blur combined with opacity."""
        stack = EffectStack()
        
        blur = BlurEffect(mode="gaussian", radius=5)
        opacity = OpacityEffect(value=0.8)
        
        effect_blur = LayerEffect(effect_config=blur, order=0)
        effect_opacity = LayerEffect(effect_config=opacity, order=1)
        
        stack.add_effect(effect_blur)
        stack.add_effect(effect_opacity)
        
        self.assertEqual(len(stack.effects), 2)
    
    def test_color_effect_combination(self):
        """Test combining color effects (grayscale + sepia)."""
        stack = EffectStack()
        
        gray = GrayscaleEffect(amount=0.5)
        sepia = SepiaEffect(amount=0.5)
        
        effect_gray = LayerEffect(effect_config=gray, order=0)
        effect_sepia = LayerEffect(effect_config=sepia, order=1)
        
        stack.add_effect(effect_gray)
        stack.add_effect(effect_sepia)
        
        self.assertEqual(len(stack.get_enabled_effects()), 2)


class TestEffectValidation(unittest.TestCase):
    """Test effect input validation."""
    
    def test_invalid_blur_radius(self):
        """Test blur with invalid radius."""
        with self.assertRaises(ValueError):
            BlurEffect(radius=0)  # Min is 1
        
        with self.assertRaises(ValueError):
            BlurEffect(radius=100)  # Max is 50
    
    def test_invalid_opacity_values(self):
        """Test opacity validation."""
        with self.assertRaises(ValueError):
            OpacityEffect(value=-0.1)
        
        with self.assertRaises(ValueError):
            OpacityEffect(value=1.1)
    
    def test_invalid_vignette_radius(self):
        """Test vignette radius validation."""
        with self.assertRaises(ValueError):
            VignetteEffect(radius=0.0)  # Min is 0.1


if __name__ == "__main__":
    unittest.main()
