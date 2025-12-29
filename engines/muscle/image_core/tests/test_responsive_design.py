"""Tests for responsive design engine."""

import unittest
from engines.image_core.responsive_design import (
    ResponsiveDesignEngine, ResponsiveComposition, ResponsiveLayer,
    ViewportConfig, ViewportSize, BreakpointBehavior, BreakpointGuide
)
from engines.image_core.models import ImageComposition, ImageLayer


class TestViewportConfig(unittest.TestCase):
    """Test viewport configuration."""
    
    def test_viewport_creation(self):
        """Test creating viewport configuration."""
        viewport = ViewportConfig(
            name=ViewportSize.MOBILE_SMALL,
            width=320,
            height=568,
            scale=0.167
        )
        
        self.assertEqual(viewport.width, 320)
        self.assertEqual(viewport.height, 568)
        self.assertEqual(viewport.scale, 0.167)
    
    def test_viewport_to_dict(self):
        """Test converting viewport to dictionary."""
        viewport = ViewportConfig(
            name=ViewportSize.MOBILE_MEDIUM,
            width=375,
            height=667
        )
        
        data = viewport.to_dict()
        
        self.assertEqual(data["name"], "mobile-medium")
        self.assertEqual(data["width"], 375)
        self.assertEqual(data["height"], 667)


class TestResponsiveLayer(unittest.TestCase):
    """Test responsive layer."""
    
    def test_responsive_layer_creation(self):
        """Test creating responsive layer."""
        layer = ResponsiveLayer(
            layer_id="title",
            layer_name="Title",
            base_x=100,
            base_y=100,
            base_width=800,
            base_height=200
        )
        
        self.assertEqual(layer.layer_id, "title")
        self.assertEqual(layer.base_width, 800)
    
    def test_layer_dimensions_for_viewport(self):
        """Test getting layer dimensions for viewport."""
        layer = ResponsiveLayer(
            layer_id="test",
            layer_name="Test",
            base_x=100,
            base_y=100,
            base_width=800,
            base_height=200,
            scale_with_viewport=True
        )
        
        # Desktop viewport (1.0 scale)
        viewport_desktop = ViewportConfig(ViewportSize.DESKTOP_MEDIUM, 1920, 1080, scale=1.0)
        dims = layer.get_dimensions_for_viewport(viewport_desktop)
        self.assertEqual(dims[2], 800)  # Width unchanged at scale 1.0
        
        # Mobile viewport (0.5 scale)
        viewport_mobile = ViewportConfig(ViewportSize.MOBILE_MEDIUM, 375, 667, scale=0.5)
        dims = layer.get_dimensions_for_viewport(viewport_mobile)
        self.assertEqual(dims[2], 400)  # Width scaled by 0.5
    
    def test_layer_hidden_on_mobile(self):
        """Test layer hidden on mobile."""
        layer = ResponsiveLayer(
            layer_id="sidebar",
            layer_name="Sidebar",
            base_x=1200,
            base_y=0,
            base_width=720,
            base_height=1080,
            breakpoint_behavior=BreakpointBehavior.HIDDEN_MOBILE
        )
        
        # Should be visible on desktop
        viewport_desktop = ViewportConfig(ViewportSize.DESKTOP_MEDIUM, 1920, 1080)
        dims = layer.get_dimensions_for_viewport(viewport_desktop)
        self.assertIsNotNone(dims)
        
        # Should be hidden on mobile
        viewport_mobile = ViewportConfig(ViewportSize.MOBILE_SMALL, 320, 568)
        dims = layer.get_dimensions_for_viewport(viewport_mobile)
        self.assertIsNone(dims)
    
    def test_layer_visible_desktop_only(self):
        """Test layer visible on desktop only."""
        layer = ResponsiveLayer(
            layer_id="ads",
            layer_name="Ads",
            base_x=0,
            base_y=0,
            base_width=300,
            base_height=600,
            breakpoint_behavior=BreakpointBehavior.VISIBLE_DESKTOP_ONLY
        )
        
        # Should be hidden on mobile
        viewport_mobile = ViewportConfig(ViewportSize.MOBILE_MEDIUM, 375, 667)
        dims = layer.get_dimensions_for_viewport(viewport_mobile)
        self.assertIsNone(dims)
        
        # Should be hidden on tablet
        viewport_tablet = ViewportConfig(ViewportSize.TABLET_PORTRAIT, 768, 1024)
        dims = layer.get_dimensions_for_viewport(viewport_tablet)
        self.assertIsNone(dims)
        
        # Should be visible on desktop
        viewport_desktop = ViewportConfig(ViewportSize.DESKTOP_MEDIUM, 1920, 1080)
        dims = layer.get_dimensions_for_viewport(viewport_desktop)
        self.assertIsNotNone(dims)
    
    def test_layer_min_width_constraint(self):
        """Test layer min width constraint."""
        layer = ResponsiveLayer(
            layer_id="content",
            layer_name="Content",
            base_x=0,
            base_y=0,
            base_width=800,
            base_height=600,
            min_width=600
        )
        
        # Should be hidden on smaller viewport
        viewport_small = ViewportConfig(ViewportSize.MOBILE_SMALL, 320, 568)
        dims = layer.get_dimensions_for_viewport(viewport_small)
        self.assertIsNone(dims)
        
        # Should be visible on larger viewport
        viewport_large = ViewportConfig(ViewportSize.TABLET_PORTRAIT, 768, 1024)
        dims = layer.get_dimensions_for_viewport(viewport_large)
        self.assertIsNotNone(dims)


class TestResponsiveComposition(unittest.TestCase):
    """Test responsive composition."""
    
    def test_responsive_composition_creation(self):
        """Test creating responsive composition."""
        comp = ResponsiveComposition(
            base_width=1920,
            base_height=1080,
            background_color="#FFFFFF"
        )
        
        self.assertEqual(comp.base_width, 1920)
        self.assertEqual(comp.base_height, 1080)
    
    def test_add_layer(self):
        """Test adding layer to composition."""
        comp = ResponsiveComposition(
            base_width=1920,
            base_height=1080,
            background_color="#FFFFFF"
        )
        
        layer = ResponsiveLayer(
            layer_id="test",
            layer_name="Test",
            base_x=0, base_y=0,
            base_width=100, base_height=100
        )
        
        comp.add_layer(layer)
        
        self.assertEqual(len(comp.layers), 1)
        self.assertEqual(comp.layers[0].layer_id, "test")
    
    def test_add_viewport(self):
        """Test adding viewport to composition."""
        comp = ResponsiveComposition(
            base_width=1920,
            base_height=1080,
            background_color="#FFFFFF"
        )
        
        viewport = ViewportConfig(ViewportSize.MOBILE_SMALL, 320, 568)
        comp.add_viewport(viewport)
        
        self.assertEqual(len(comp.viewports), 1)
    
    def test_get_default_viewports(self):
        """Test getting default viewports."""
        comp = ResponsiveComposition(
            base_width=1920,
            base_height=1080,
            background_color="#FFFFFF"
        )
        
        viewports = comp.get_default_viewports()
        
        self.assertEqual(len(viewports), 9)
        self.assertEqual(viewports[0].name, ViewportSize.MOBILE_SMALL)
        self.assertEqual(viewports[-1].name, ViewportSize.ULTRAWIDE)


class TestResponsiveDesignEngine(unittest.TestCase):
    """Test responsive design engine."""
    
    def test_create_responsive_composition(self):
        """Test creating responsive composition from regular composition."""
        comp = ImageComposition(
            width=1920, height=1080,
            background_color="#FFFFFF",
            layers=[
                ImageLayer(id="header", name="Header", x=0, y=0, width=1920, height=200),
                ImageLayer(id="content", name="Content", x=0, y=200, width=1920, height=880),
            ],
            tenant_id="test",
            env="test"
        )
        
        responsive = ResponsiveDesignEngine.create_responsive_composition(comp)
        
        self.assertEqual(len(responsive.layers), 2)
        self.assertEqual(responsive.layers[0].layer_id, "header")
    
    def test_generate_variants(self):
        """Test generating responsive variants."""
        responsive_comp = ResponsiveComposition(
            base_width=1920,
            base_height=1080,
            background_color="#FFFFFF"
        )
        
        responsive_comp.add_layer(ResponsiveLayer(
            layer_id="content",
            layer_name="Content",
            base_x=0, base_y=0,
            base_width=1920, base_height=1080
        ))
        
        variants = ResponsiveDesignEngine.generate_variants(responsive_comp)
        
        self.assertEqual(len(variants), 9)  # Default 9 viewports
        
        # Check first variant (mobile-small)
        self.assertEqual(variants[0].viewport.width, 320)
        self.assertEqual(variants[0].composition_width, 320)
    
    def test_responsive_images_sizes(self):
        """Test responsive image size calculation."""
        sizes = ResponsiveDesignEngine.get_responsive_images_sizes(1920)
        
        self.assertIn("mobile-1x", sizes)
        self.assertIn("desktop-2x", sizes)
        self.assertEqual(sizes["mobile-1x"], 480)  # 1920 * 0.25
        self.assertEqual(sizes["desktop-1x"], 1920)
        self.assertEqual(sizes["desktop-2x"], 3840)
    
    def test_font_scaling(self):
        """Test font size scaling."""
        # 16px at 1920px width
        size_mobile = ResponsiveDesignEngine.calculate_font_scaling(16, 1920, 320)
        size_desktop = ResponsiveDesignEngine.calculate_font_scaling(16, 1920, 1920)
        
        self.assertLess(size_mobile, size_desktop)
        self.assertEqual(size_desktop, 16)  # No scaling at 1.0
    
    def test_padding_scaling(self):
        """Test padding scaling."""
        # 16px at 1920px width
        padding_mobile = ResponsiveDesignEngine.calculate_padding_scaling(16, 1920, 320)
        padding_desktop = ResponsiveDesignEngine.calculate_padding_scaling(16, 1920, 1920)
        
        self.assertLess(padding_mobile, padding_desktop)
        self.assertEqual(padding_desktop, 16)  # No scaling at 1.0
    
    def test_breakpoint_guide_generation(self):
        """Test breakpoint guide generation."""
        responsive_comp = ResponsiveComposition(
            base_width=1920,
            base_height=1080,
            background_color="#FFFFFF"
        )
        
        responsive_comp.add_layer(ResponsiveLayer(
            layer_id="sidebar",
            layer_name="Sidebar",
            base_x=1200, base_y=0,
            base_width=720, base_height=1080,
            breakpoint_behavior=BreakpointBehavior.HIDDEN_MOBILE
        ))
        
        responsive_comp.add_layer(ResponsiveLayer(
            layer_id="content",
            layer_name="Content",
            base_x=0, base_y=0,
            base_width=1200, base_height=1080
        ))
        
        viewport_mobile = ViewportConfig(ViewportSize.MOBILE_SMALL, 320, 568)
        guide = ResponsiveDesignEngine.generate_breakpoint_guide(responsive_comp, viewport_mobile)
        
        self.assertEqual(guide.target_layers, 2)
        self.assertEqual(guide.visible_layers, 1)  # Sidebar hidden
        self.assertEqual(guide.hidden_layers, 1)
        self.assertGreater(guide.recommended_font_size, 0)
    
    def test_css_media_queries(self):
        """Test CSS media query generation."""
        responsive_comp = ResponsiveComposition(
            base_width=1920,
            base_height=1080,
            background_color="#FFFFFF"
        )
        
        responsive_comp.add_layer(ResponsiveLayer(
            layer_id="header",
            layer_name="Header",
            base_x=0, base_y=0,
            base_width=1920, base_height=200
        ))
        
        viewports = [
            ViewportConfig(ViewportSize.MOBILE_SMALL, 320, 568),
            ViewportConfig(ViewportSize.DESKTOP_MEDIUM, 1920, 1080),
        ]
        
        css_queries = ResponsiveDesignEngine.generate_css_media_queries(responsive_comp, viewports)
        
        self.assertEqual(len(css_queries), 2)
        self.assertIn("mobile-small", css_queries)
        self.assertIn("@media", css_queries["mobile-small"])
    
    def test_tailwindcss_breakpoints(self):
        """Test Tailwind CSS breakpoint config."""
        breakpoints = ResponsiveDesignEngine.get_tailwindcss_breakpoints()
        
        self.assertIn("sm", breakpoints)
        self.assertIn("lg", breakpoints)
        self.assertEqual(breakpoints["sm"], "640px")
    
    def test_layer_density_analysis(self):
        """Test layer density analysis."""
        responsive_comp = ResponsiveComposition(
            base_width=1920,
            base_height=1080,
            background_color="#FFFFFF"
        )
        
        # Add multiple layers
        for i in range(5):
            responsive_comp.add_layer(ResponsiveLayer(
                layer_id=f"layer-{i}",
                layer_name=f"Layer {i}",
                base_x=i*100, base_y=0,
                base_width=100, base_height=100
            ))
        
        density = ResponsiveDesignEngine.analyze_layer_density(responsive_comp)
        
        self.assertIn("mobile-small", density)
        self.assertIn("desktop-medium", density)
        self.assertGreater(density["mobile-small"], 0)


class TestResponsiveEdgeCases(unittest.TestCase):
    """Test edge cases in responsive design."""
    
    def test_layer_hidden_tablet(self):
        """Test layer hidden on tablet."""
        layer = ResponsiveLayer(
            layer_id="feature",
            layer_name="Feature",
            base_x=0, base_y=0,
            base_width=100, base_height=100,
            breakpoint_behavior=BreakpointBehavior.HIDDEN_TABLET
        )
        
        # Should be visible on mobile
        viewport_mobile = ViewportConfig(ViewportSize.MOBILE_SMALL, 320, 568)
        self.assertIsNotNone(layer.get_dimensions_for_viewport(viewport_mobile))
        
        # Should be hidden on tablet
        viewport_tablet = ViewportConfig(ViewportSize.TABLET_PORTRAIT, 768, 1024)
        self.assertIsNone(layer.get_dimensions_for_viewport(viewport_tablet))
        
        # Should be visible on desktop
        viewport_desktop = ViewportConfig(ViewportSize.DESKTOP_MEDIUM, 1920, 1080)
        self.assertIsNotNone(layer.get_dimensions_for_viewport(viewport_desktop))
    
    def test_layer_always_visible(self):
        """Test layer always visible."""
        layer = ResponsiveLayer(
            layer_id="logo",
            layer_name="Logo",
            base_x=10, base_y=10,
            base_width=50, base_height=50,
            breakpoint_behavior=BreakpointBehavior.ALWAYS_VISIBLE,
            scale_with_viewport=False  # Don't scale
        )
        
        for width in [320, 768, 1920]:
            viewport = ViewportConfig(ViewportSize.MOBILE_SMALL, width, 600)
            dims = layer.get_dimensions_for_viewport(viewport)
            self.assertIsNotNone(dims)
            # Dimensions should be unchanged
            self.assertEqual(dims[2], 50)


if __name__ == "__main__":
    unittest.main()
