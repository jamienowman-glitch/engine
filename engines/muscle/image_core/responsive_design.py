"""Responsive design engine for automatic viewport variations."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime


class ViewportSize(str, Enum):
    """Standard viewport sizes."""
    MOBILE_SMALL = "mobile-small"  # 320px
    MOBILE_MEDIUM = "mobile-medium"  # 375px
    MOBILE_LARGE = "mobile-large"  # 480px
    TABLET_PORTRAIT = "tablet-portrait"  # 768px
    TABLET_LANDSCAPE = "tablet-landscape"  # 1024px
    DESKTOP_SMALL = "desktop-small"  # 1280px
    DESKTOP_MEDIUM = "desktop-medium"  # 1920px
    DESKTOP_LARGE = "desktop-large"  # 2560px
    ULTRAWIDE = "ultrawide"  # 3840px


class BreakpointBehavior(str, Enum):
    """Layer behavior at breakpoints."""
    ALWAYS_VISIBLE = "always-visible"  # Show on all sizes
    HIDDEN_MOBILE = "hidden-mobile"  # Hide on mobile
    HIDDEN_TABLET = "hidden-tablet"  # Hide on tablet
    VISIBLE_DESKTOP_ONLY = "visible-desktop-only"  # Only show on desktop
    RESPONSIVE = "responsive"  # Adjust size/position based on viewport


@dataclass
class ViewportConfig:
    """Configuration for a viewport/breakpoint."""
    name: ViewportSize
    width: int
    height: int
    scale: float = 1.0  # Scale factor from base
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "name": self.name.value,
            "width": self.width,
            "height": self.height,
            "scale": self.scale,
        }


@dataclass
class ResponsiveLayer:
    """Layer configuration for responsive design."""
    layer_id: str
    layer_name: str
    base_x: float
    base_y: float
    base_width: float
    base_height: float
    breakpoint_behavior: BreakpointBehavior = BreakpointBehavior.RESPONSIVE
    min_width: Optional[int] = None  # Minimum width to display
    max_width: Optional[int] = None  # Maximum width to display
    scale_with_viewport: bool = True  # Whether to scale with viewport
    keep_aspect_ratio: bool = True  # Whether to maintain aspect ratio
    
    def get_dimensions_for_viewport(
        self, viewport: ViewportConfig
    ) -> Optional[Tuple[float, float, float, float]]:
        """
        Get layer dimensions for a specific viewport.
        
        Returns:
            Tuple of (x, y, width, height) or None if hidden at this breakpoint
        """
        # Check visibility at breakpoint
        if self.breakpoint_behavior == BreakpointBehavior.HIDDEN_MOBILE and viewport.width < 768:
            return None
        if self.breakpoint_behavior == BreakpointBehavior.HIDDEN_TABLET and 768 <= viewport.width < 1280:
            return None
        if self.breakpoint_behavior == BreakpointBehavior.VISIBLE_DESKTOP_ONLY and viewport.width < 1280:
            return None
        
        # Check min/max width constraints
        if self.min_width and viewport.width < self.min_width:
            return None
        if self.max_width and viewport.width > self.max_width:
            return None
        
        # Calculate dimensions
        if self.scale_with_viewport and self.breakpoint_behavior == BreakpointBehavior.RESPONSIVE:
            # Scale dimensions based on viewport scale
            new_x = self.base_x * viewport.scale
            new_y = self.base_y * viewport.scale
            new_width = self.base_width * viewport.scale
            new_height = self.base_height * viewport.scale
        else:
            # Keep original dimensions
            new_x = self.base_x
            new_y = self.base_y
            new_width = self.base_width
            new_height = self.base_height
        
        return (new_x, new_y, new_width, new_height)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "layer_id": self.layer_id,
            "layer_name": self.layer_name,
            "base_x": self.base_x,
            "base_y": self.base_y,
            "base_width": self.base_width,
            "base_height": self.base_height,
            "breakpoint_behavior": self.breakpoint_behavior.value,
            "min_width": self.min_width,
            "max_width": self.max_width,
            "scale_with_viewport": self.scale_with_viewport,
            "keep_aspect_ratio": self.keep_aspect_ratio,
        }


@dataclass
class ResponsiveComposition:
    """Composition with responsive layer definitions."""
    base_width: int  # Desktop width (default 1920)
    base_height: int  # Desktop height (default 1080)
    background_color: str
    layers: List[ResponsiveLayer] = field(default_factory=list)
    viewports: List[ViewportConfig] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def add_layer(self, layer: ResponsiveLayer) -> None:
        """Add a responsive layer."""
        self.layers.append(layer)
    
    def add_viewport(self, viewport: ViewportConfig) -> None:
        """Add a viewport configuration."""
        self.viewports.append(viewport)
    
    def get_default_viewports(self) -> List[ViewportConfig]:
        """Get default viewport configurations."""
        return [
            ViewportConfig(ViewportSize.MOBILE_SMALL, 320, 568, 0.167),
            ViewportConfig(ViewportSize.MOBILE_MEDIUM, 375, 667, 0.195),
            ViewportConfig(ViewportSize.MOBILE_LARGE, 480, 854, 0.25),
            ViewportConfig(ViewportSize.TABLET_PORTRAIT, 768, 1024, 0.4),
            ViewportConfig(ViewportSize.TABLET_LANDSCAPE, 1024, 768, 0.533),
            ViewportConfig(ViewportSize.DESKTOP_SMALL, 1280, 720, 0.667),
            ViewportConfig(ViewportSize.DESKTOP_MEDIUM, 1920, 1080, 1.0),
            ViewportConfig(ViewportSize.DESKTOP_LARGE, 2560, 1440, 1.333),
            ViewportConfig(ViewportSize.ULTRAWIDE, 3840, 2160, 2.0),
        ]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "base_width": self.base_width,
            "base_height": self.base_height,
            "background_color": self.background_color,
            "layers": [l.to_dict() for l in self.layers],
            "viewports": [v.to_dict() for v in self.viewports],
            "created_at": self.created_at,
        }


@dataclass
class ResponsiveVariant:
    """A responsive variant for specific viewport."""
    viewport: ViewportConfig
    composition_width: int
    composition_height: int
    background_color: str
    layers: List[Dict] = field(default_factory=list)  # Layer data with viewport-specific dimensions
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "viewport": self.viewport.to_dict(),
            "composition_width": self.composition_width,
            "composition_height": self.composition_height,
            "background_color": self.background_color,
            "layers": self.layers,
        }


@dataclass
class BreakpointGuide:
    """Guide for responsive design."""
    breakpoint_name: str
    width: int
    target_layers: int
    visible_layers: int
    hidden_layers: int
    recommended_font_size: int  # Recommended font size adjustment
    recommended_padding: int  # Recommended padding adjustment
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "breakpoint_name": self.breakpoint_name,
            "width": self.width,
            "target_layers": self.target_layers,
            "visible_layers": self.visible_layers,
            "hidden_layers": self.hidden_layers,
            "recommended_font_size": self.recommended_font_size,
            "recommended_padding": self.recommended_padding,
        }


class ResponsiveDesignEngine:
    """Generate responsive design variants from composition."""
    
    @staticmethod
    def create_responsive_composition(
        base_composition,
        base_width: int = 1920,
        base_height: int = 1080
    ) -> ResponsiveComposition:
        """
        Create responsive composition from regular composition.
        
        Converts layers to responsive layers with default behavior.
        """
        responsive_comp = ResponsiveComposition(
            base_width=base_width,
            base_height=base_height,
            background_color=base_composition.background_color,
        )
        
        # Convert layers to responsive layers
        for layer in base_composition.layers:
            responsive_layer = ResponsiveLayer(
                layer_id=layer.id,
                layer_name=layer.name,
                base_x=getattr(layer, 'x', 0),
                base_y=getattr(layer, 'y', 0),
                base_width=getattr(layer, 'width', 100),
                base_height=getattr(layer, 'height', 100),
                breakpoint_behavior=BreakpointBehavior.RESPONSIVE,
                scale_with_viewport=True,
            )
            responsive_comp.add_layer(responsive_layer)
        
        return responsive_comp
    
    @staticmethod
    def generate_variants(
        responsive_comp: ResponsiveComposition,
        viewports: Optional[List[ViewportConfig]] = None
    ) -> List[ResponsiveVariant]:
        """Generate responsive variants for all viewports."""
        if viewports is None:
            viewports = responsive_comp.get_default_viewports()
        
        variants = []
        
        for viewport in viewports:
            # Calculate new dimensions based on viewport
            variant_width = viewport.width
            variant_height = viewport.height
            
            # Build layer data for this viewport
            variant_layers = []
            
            for layer in responsive_comp.layers:
                dims = layer.get_dimensions_for_viewport(viewport)
                
                if dims is not None:
                    x, y, width, height = dims
                    variant_layers.append({
                        "layer_id": layer.layer_id,
                        "layer_name": layer.layer_name,
                        "x": int(x),
                        "y": int(y),
                        "width": int(width),
                        "height": int(height),
                        "visible": True,
                        "breakpoint_behavior": layer.breakpoint_behavior.value,
                    })
                else:
                    # Layer is hidden at this breakpoint
                    variant_layers.append({
                        "layer_id": layer.layer_id,
                        "layer_name": layer.layer_name,
                        "visible": False,
                        "breakpoint_behavior": layer.breakpoint_behavior.value,
                    })
            
            variant = ResponsiveVariant(
                viewport=viewport,
                composition_width=variant_width,
                composition_height=variant_height,
                background_color=responsive_comp.background_color,
                layers=variant_layers,
            )
            variants.append(variant)
        
        return variants
    
    @staticmethod
    def get_responsive_images_sizes(
        base_width: int = 1920
    ) -> Dict[str, int]:
        """Get recommended image sizes for responsive design."""
        return {
            "mobile-1x": int(base_width * 0.25),
            "mobile-2x": int(base_width * 0.5),
            "tablet-1x": int(base_width * 0.5),
            "tablet-2x": int(base_width),
            "desktop-1x": base_width,
            "desktop-2x": base_width * 2,
        }
    
    @staticmethod
    def calculate_font_scaling(
        base_font_size: int,
        base_width: int,
        viewport_width: int
    ) -> int:
        """Calculate font size scaling for viewport."""
        # Scale linearly based on viewport width
        scale = min(viewport_width / base_width, 1.0)
        # Minimum scale of 0.75 for mobile
        scale = max(scale, 0.75)
        return int(base_font_size * scale)
    
    @staticmethod
    def calculate_padding_scaling(
        base_padding: int,
        base_width: int,
        viewport_width: int
    ) -> int:
        """Calculate padding scaling for viewport."""
        scale = min(viewport_width / base_width, 1.0)
        scale = max(scale, 0.5)  # Minimum scale of 0.5
        return int(base_padding * scale)
    
    @staticmethod
    def generate_breakpoint_guide(
        responsive_comp: ResponsiveComposition,
        viewport: ViewportConfig
    ) -> BreakpointGuide:
        """Generate design guide for a breakpoint."""
        visible_count = 0
        hidden_count = 0
        
        for layer in responsive_comp.layers:
            dims = layer.get_dimensions_for_viewport(viewport)
            if dims is not None:
                visible_count += 1
            else:
                hidden_count += 1
        
        # Recommend font size (in pixels)
        recommended_font = ResponsiveDesignEngine.calculate_font_scaling(16, 1920, viewport.width)
        
        # Recommend padding (in pixels)
        recommended_padding = ResponsiveDesignEngine.calculate_padding_scaling(16, 1920, viewport.width)
        
        return BreakpointGuide(
            breakpoint_name=viewport.name.value,
            width=viewport.width,
            target_layers=len(responsive_comp.layers),
            visible_layers=visible_count,
            hidden_layers=hidden_count,
            recommended_font_size=recommended_font,
            recommended_padding=recommended_padding,
        )
    
    @staticmethod
    def generate_css_media_queries(
        responsive_comp: ResponsiveComposition,
        viewports: Optional[List[ViewportConfig]] = None
    ) -> Dict[str, str]:
        """Generate CSS media queries for responsive design."""
        if viewports is None:
            viewports = responsive_comp.get_default_viewports()
        
        css_queries = {}
        
        for viewport in viewports:
            css = f"@media (max-width: {viewport.width}px) {{\n"
            css += f"  .composition {{\n"
            css += f"    width: {viewport.width}px;\n"
            css += f"    height: {viewport.height}px;\n"
            css += f"  }}\n"
            
            # Add layer-specific rules
            for layer in responsive_comp.layers:
                dims = layer.get_dimensions_for_viewport(viewport)
                
                if dims is None:
                    css += f"  .{layer.layer_id} {{ display: none; }}\n"
                else:
                    x, y, width, height = dims
                    css += f"  .{layer.layer_id} {{\n"
                    css += f"    position: absolute;\n"
                    css += f"    left: {int(x)}px;\n"
                    css += f"    top: {int(y)}px;\n"
                    css += f"    width: {int(width)}px;\n"
                    css += f"    height: {int(height)}px;\n"
                    css += f"  }}\n"
            
            css += "}\n"
            css_queries[viewport.name.value] = css
        
        return css_queries
    
    @staticmethod
    def get_tailwindcss_breakpoints() -> Dict[str, str]:
        """Get Tailwind CSS breakpoint configuration."""
        return {
            "sm": "640px",
            "md": "768px",
            "lg": "1024px",
            "xl": "1280px",
            "2xl": "1536px",
        }
    
    @staticmethod
    def analyze_layer_density(
        responsive_comp: ResponsiveComposition
    ) -> Dict[str, float]:
        """Analyze layer density (complexity) at different breakpoints."""
        viewports = responsive_comp.get_default_viewports()
        density = {}
        
        for viewport in viewports:
            visible_layers = sum(
                1 for layer in responsive_comp.layers
                if layer.get_dimensions_for_viewport(viewport) is not None
            )
            
            # Density = visible layers / viewport width * 1000
            d = (visible_layers / viewport.width) * 1000
            density[viewport.name.value] = round(d, 2)
        
        return density


# Singleton accessor
_responsive_engine_instance = None


def get_responsive_design_engine() -> ResponsiveDesignEngine:
    """Get singleton ResponsiveDesignEngine instance."""
    global _responsive_engine_instance
    if _responsive_engine_instance is None:
        _responsive_engine_instance = ResponsiveDesignEngine()
    return _responsive_engine_instance
