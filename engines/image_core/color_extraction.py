"""Color extraction and palette generation from compositions."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import re
from datetime import datetime


class ColorFormat(str, Enum):
    """Supported color formats."""
    HEX = "hex"
    RGB = "rgb"
    HSL = "hsl"
    HSV = "hsv"


@dataclass
class ColorMetrics:
    """Metrics for a color."""
    hex_value: str
    rgb: Tuple[int, int, int]
    hsl: Tuple[int, int, int]  # (h: 0-360, s: 0-100, l: 0-100)
    hsv: Tuple[int, int, int]  # (h: 0-360, s: 0-100, v: 0-100)
    luminance: float  # 0-1 for brightness
    frequency: int = 1  # How many times color appears
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "hex": self.hex_value,
            "rgb": {"r": self.rgb[0], "g": self.rgb[1], "b": self.rgb[2]},
            "hsl": {"h": self.hsl[0], "s": self.hsl[1], "l": self.hsl[2]},
            "hsv": {"h": self.hsv[0], "s": self.hsv[1], "v": self.hsv[2]},
            "luminance": round(self.luminance, 3),
            "frequency": self.frequency,
        }


@dataclass
class ColorPalette:
    """A color palette extracted from composition."""
    primary: ColorMetrics
    secondary: Optional[ColorMetrics] = None
    accent: Optional[ColorMetrics] = None
    colors: List[ColorMetrics] = field(default_factory=list)
    background_color: Optional[str] = None
    extracted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def get_dominant_colors(self, count: int = 5) -> List[ColorMetrics]:
        """Get top N dominant colors sorted by frequency."""
        sorted_colors = sorted(self.colors, key=lambda c: c.frequency, reverse=True)
        return sorted_colors[:count]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "primary": self.primary.to_dict(),
            "secondary": self.secondary.to_dict() if self.secondary else None,
            "accent": self.accent.to_dict() if self.accent else None,
            "all_colors": [c.to_dict() for c in self.colors],
            "background_color": self.background_color,
            "extracted_at": self.extracted_at,
        }


@dataclass
class ColorVariation:
    """A color variation (lighter/darker/etc)."""
    base_color: str  # Hex
    hue_shift: int = 0  # -360 to 360
    saturation_adjust: int = 0  # -100 to 100
    lightness_adjust: int = 0  # -100 to 100
    result_color: str = ""  # Hex result
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "base_color": self.base_color,
            "hue_shift": self.hue_shift,
            "saturation_adjust": self.saturation_adjust,
            "lightness_adjust": self.lightness_adjust,
            "result_color": self.result_color,
        }


@dataclass
class AccessibilityReport:
    """WCAG accessibility analysis for color pair."""
    foreground_color: str
    background_color: str
    contrast_ratio: float  # WCAG contrast ratio
    wcag_aa_compliant: bool  # Passes WCAG AA (4.5:1 for text)
    wcag_aaa_compliant: bool  # Passes WCAG AAA (7:1 for text)
    wcag_large_text_aa: bool  # Passes WCAG AA for large text (3:1)
    wcag_large_text_aaa: bool  # Passes WCAG AAA for large text (4.5:1)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "foreground_color": self.foreground_color,
            "background_color": self.background_color,
            "contrast_ratio": round(self.contrast_ratio, 2),
            "wcag_aa_compliant": self.wcag_aa_compliant,
            "wcag_aaa_compliant": self.wcag_aaa_compliant,
            "wcag_large_text_aa": self.wcag_large_text_aa,
            "wcag_large_text_aaa": self.wcag_large_text_aaa,
        }


class ColorExtractor:
    """Extract colors and generate palettes from compositions."""
    
    @staticmethod
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    @staticmethod
    def rgb_to_hex(r: int, g: int, b: int) -> str:
        """Convert RGB to hex."""
        return f"#{r:02x}{g:02x}{b:02x}".upper()
    
    @staticmethod
    def rgb_to_hsl(r: int, g: int, b: int) -> Tuple[int, int, int]:
        """Convert RGB to HSL."""
        r, g, b = r / 255.0, g / 255.0, b / 255.0
        max_c = max(r, g, b)
        min_c = min(r, g, b)
        l = (max_c + min_c) / 2.0
        
        if max_c == min_c:
            h = s = 0
        else:
            d = max_c - min_c
            s = d / (2.0 - max_c - min_c) if l > 0.5 else d / (max_c + min_c)
            
            if max_c == r:
                h = (60 * ((g - b) / d) + 360) % 360
            elif max_c == g:
                h = (60 * ((b - r) / d) + 120) % 360
            else:
                h = (60 * ((r - g) / d) + 240) % 360
        
        return (int(h), int(s * 100), int(l * 100))
    
    @staticmethod
    def rgb_to_hsv(r: int, g: int, b: int) -> Tuple[int, int, int]:
        """Convert RGB to HSV."""
        r, g, b = r / 255.0, g / 255.0, b / 255.0
        max_c = max(r, g, b)
        min_c = min(r, g, b)
        v = max_c
        
        if max_c == min_c:
            h = s = 0
        else:
            d = max_c - min_c
            s = d / max_c
            
            if max_c == r:
                h = (60 * ((g - b) / d) + 360) % 360
            elif max_c == g:
                h = (60 * ((b - r) / d) + 120) % 360
            else:
                h = (60 * ((r - g) / d) + 240) % 360
        
        return (int(h), int(s * 100), int(v * 100))
    
    @staticmethod
    def hsl_to_rgb(h: int, s: int, l: int) -> Tuple[int, int, int]:
        """Convert HSL to RGB."""
        s, l = s / 100.0, l / 100.0
        
        def hue_to_rgb(p, q, t):
            if t < 0:
                t += 1
            if t > 1:
                t -= 1
            if t < 1/6:
                return p + (q - p) * 6 * t
            if t < 1/2:
                return q
            if t < 2/3:
                return p + (q - p) * (2/3 - t) * 6
            return p
        
        if s == 0:
            r = g = b = l
        else:
            q = l * (1 + s) if l < 0.5 else l + s - l * s
            p = 2 * l - q
            r = hue_to_rgb(p, q, h / 360.0 + 1/3)
            g = hue_to_rgb(p, q, h / 360.0)
            b = hue_to_rgb(p, q, h / 360.0 - 1/3)
        
        return (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))
    
    @staticmethod
    def calculate_luminance(r: int, g: int, b: int) -> float:
        """Calculate relative luminance for WCAG contrast."""
        # sRGB to relative luminance
        r, g, b = r / 255.0, g / 255.0, b / 255.0
        
        r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
        g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
        b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
        
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    
    @staticmethod
    def create_color_metrics(hex_color: str, frequency: int = 1) -> ColorMetrics:
        """Create color metrics from hex color."""
        # Normalize hex color
        hex_color = hex_color.lstrip('#').upper()
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        hex_color = f"#{hex_color}"
        
        rgb = ColorExtractor.hex_to_rgb(hex_color)
        hsl = ColorExtractor.rgb_to_hsl(*rgb)
        hsv = ColorExtractor.rgb_to_hsv(*rgb)
        luminance = ColorExtractor.calculate_luminance(*rgb)
        
        return ColorMetrics(
            hex_value=hex_color,
            rgb=rgb,
            hsl=hsl,
            hsv=hsv,
            luminance=luminance,
            frequency=frequency,
        )
    
    @staticmethod
    def extract_from_composition(composition) -> ColorPalette:
        """Extract color palette from composition."""
        color_freq: Dict[str, int] = {}
        
        # Collect background color
        bg_color = composition.background_color or "#FFFFFF"
        color_freq[bg_color] = color_freq.get(bg_color, 0) + 1
        
        # Collect colors from layers
        for layer in composition.layers:
            if hasattr(layer, 'color') and layer.color:
                color_freq[layer.color] = color_freq.get(layer.color, 0) + 1
            if hasattr(layer, 'text_color') and layer.text_color:
                color_freq[layer.text_color] = color_freq.get(layer.text_color, 0) + 1
            if hasattr(layer, 'stroke_color') and layer.stroke_color:
                color_freq[layer.stroke_color] = color_freq.get(layer.stroke_color, 0) + 1
        
        # Create metrics for each color
        color_metrics = []
        for hex_color, freq in color_freq.items():
            if hex_color:
                metrics = ColorExtractor.create_color_metrics(hex_color, freq)
                color_metrics.append(metrics)
        
        # Sort by frequency
        color_metrics.sort(key=lambda c: c.frequency, reverse=True)
        
        # Assign primary, secondary, accent
        primary = color_metrics[0] if color_metrics else ColorExtractor.create_color_metrics("#FFFFFF")
        secondary = color_metrics[1] if len(color_metrics) > 1 else None
        accent = color_metrics[2] if len(color_metrics) > 2 else None
        
        return ColorPalette(
            primary=primary,
            secondary=secondary,
            accent=accent,
            colors=color_metrics,
            background_color=bg_color,
        )
    
    @staticmethod
    def generate_palette_sizes(
        colors: List[ColorMetrics],
        sizes: Optional[List[int]] = None
    ) -> Dict[int, List[str]]:
        """Generate color palettes of different sizes."""
        if sizes is None:
            sizes = [3, 5, 8, 12]
        
        palettes = {}
        sorted_colors = sorted(colors, key=lambda c: c.frequency, reverse=True)
        
        for size in sizes:
            palette_colors = sorted_colors[:size]
            palettes[size] = [c.hex_value for c in palette_colors]
        
        return palettes
    
    @staticmethod
    def generate_variations(
        base_color: str,
        variations: Optional[List[Dict]] = None
    ) -> List[ColorVariation]:
        """Generate color variations (lighter/darker/saturated/etc)."""
        if variations is None:
            variations = [
                {"lightness_adjust": 20},  # Lighter
                {"lightness_adjust": -20},  # Darker
                {"saturation_adjust": 30},  # More saturated
                {"saturation_adjust": -30},  # Less saturated
                {"hue_shift": 30},  # Hue shift +30
                {"hue_shift": -30},  # Hue shift -30
            ]
        
        result_variations = []
        
        # Get base color HSL
        rgb = ColorExtractor.hex_to_rgb(base_color)
        h, s, l = ColorExtractor.rgb_to_hsl(*rgb)
        
        for var in variations:
            h_shift = var.get("hue_shift", 0)
            s_adjust = var.get("saturation_adjust", 0)
            l_adjust = var.get("lightness_adjust", 0)
            
            # Apply adjustments
            new_h = (h + h_shift) % 360
            new_s = max(0, min(100, s + s_adjust))
            new_l = max(0, min(100, l + l_adjust))
            
            # Convert back to RGB and hex
            new_rgb = ColorExtractor.hsl_to_rgb(new_h, new_s, new_l)
            new_hex = ColorExtractor.rgb_to_hex(*new_rgb)
            
            variation = ColorVariation(
                base_color=base_color,
                hue_shift=h_shift,
                saturation_adjust=s_adjust,
                lightness_adjust=l_adjust,
                result_color=new_hex,
            )
            result_variations.append(variation)
        
        return result_variations
    
    @staticmethod
    def check_contrast_wcag(
        foreground_color: str,
        background_color: str
    ) -> AccessibilityReport:
        """Check WCAG contrast compliance between two colors."""
        fg_rgb = ColorExtractor.hex_to_rgb(foreground_color)
        bg_rgb = ColorExtractor.hex_to_rgb(background_color)
        
        fg_luminance = ColorExtractor.calculate_luminance(*fg_rgb)
        bg_luminance = ColorExtractor.calculate_luminance(*bg_rgb)
        
        # Contrast ratio calculation
        lighter = max(fg_luminance, bg_luminance)
        darker = min(fg_luminance, bg_luminance)
        contrast_ratio = (lighter + 0.05) / (darker + 0.05)
        
        return AccessibilityReport(
            foreground_color=foreground_color,
            background_color=background_color,
            contrast_ratio=contrast_ratio,
            wcag_aa_compliant=contrast_ratio >= 4.5,  # Normal text
            wcag_aaa_compliant=contrast_ratio >= 7.0,  # Normal text AAA
            wcag_large_text_aa=contrast_ratio >= 3.0,  # Large text
            wcag_large_text_aaa=contrast_ratio >= 4.5,  # Large text AAA
        )
    
    @staticmethod
    def find_accessible_contrast(
        base_color: str,
        bg_color: str,
        target_ratio: float = 7.0
    ) -> Optional[str]:
        """Find a variation of base_color that meets contrast ratio."""
        # Get HSL
        rgb = ColorExtractor.hex_to_rgb(base_color)
        h, s, l = ColorExtractor.rgb_to_hsl(*rgb)
        
        # Try variations in lightness
        for l_adjust in range(-50, 51, 5):
            new_l = max(0, min(100, l + l_adjust))
            new_rgb = ColorExtractor.hsl_to_rgb(h, s, new_l)
            new_hex = ColorExtractor.rgb_to_hex(*new_rgb)
            
            report = ColorExtractor.check_contrast_wcag(new_hex, bg_color)
            if report.contrast_ratio >= target_ratio:
                return new_hex
        
        return None


# Singleton accessor
_color_extractor_instance = None


def get_color_extractor() -> ColorExtractor:
    """Get singleton ColorExtractor instance."""
    global _color_extractor_instance
    if _color_extractor_instance is None:
        _color_extractor_instance = ColorExtractor()
    return _color_extractor_instance
