"""Layer effects system for shadows, glows, blurs, and other visual enhancements."""

from __future__ import annotations
from typing import Literal, Optional, List, Tuple
from pydantic import BaseModel, Field, validator
from dataclasses import dataclass
from enum import Enum


class EffectType(str, Enum):
    """Available effect types."""
    SHADOW = "shadow"
    GLOW = "glow"
    BLUR = "blur"
    HIGHLIGHT = "highlight"
    VIGNETTE = "vignette"
    OPACITY = "opacity"
    INVERT = "invert"
    SEPIA = "sepia"
    GRAYSCALE = "grayscale"


class ShadowEffect(BaseModel):
    """Drop shadow or inner shadow effect."""
    type: Literal["shadow"] = "shadow"
    mode: Literal["drop", "inner"] = Field(default="drop", description="Drop or inner shadow")
    x_offset: int = Field(default=2, ge=-100, le=100, description="Horizontal offset in pixels")
    y_offset: int = Field(default=2, ge=-100, le=100, description="Vertical offset in pixels")
    blur_radius: int = Field(default=4, ge=0, le=50, description="Blur radius in pixels")
    spread_radius: int = Field(default=0, ge=-20, le=20, description="Spread radius in pixels")
    color: str = Field(default="#000000", description="Shadow color (hex)")
    opacity: float = Field(default=0.5, ge=0.0, le=1.0, description="Shadow opacity")


class GlowEffect(BaseModel):
    """Glow or outer glow effect."""
    type: Literal["glow"] = "glow"
    mode: Literal["outer", "inner"] = Field(default="outer", description="Outer or inner glow")
    blur_radius: int = Field(default=10, ge=1, le=50, description="Glow blur radius")
    spread_radius: int = Field(default=2, ge=0, le=20, description="Glow spread")
    color: str = Field(default="#FFFFFF", description="Glow color (hex)")
    opacity: float = Field(default=0.8, ge=0.0, le=1.0, description="Glow opacity")


class BlurEffect(BaseModel):
    """Blur effect (motion, gaussian, etc)."""
    type: Literal["blur"] = "blur"
    mode: Literal["gaussian", "motion", "zoom"] = Field(default="gaussian", description="Blur mode")
    radius: int = Field(default=5, ge=1, le=50, description="Blur radius")
    angle: int = Field(default=0, ge=0, le=360, description="Motion blur angle (for motion blur)")


class HighlightEffect(BaseModel):
    """Highlight or overlay effect."""
    type: Literal["highlight"] = "highlight"
    color: str = Field(default="#FFFF00", description="Highlight color")
    opacity: float = Field(default=0.3, ge=0.0, le=1.0, description="Highlight opacity")
    mode: Literal["overlay", "screen", "multiply"] = Field(default="overlay", description="Blend mode")


class VignetteEffect(BaseModel):
    """Vignette (darkened edges) effect."""
    type: Literal["vignette"] = "vignette"
    darkness: float = Field(default=0.5, ge=0.0, le=1.0, description="Vignette darkness (0-1)")
    radius: float = Field(default=0.7, ge=0.1, le=1.0, description="Vignette radius (0-1)")
    smoothness: float = Field(default=0.5, ge=0.0, le=1.0, description="Vignette smoothness")


class OpacityEffect(BaseModel):
    """Opacity/fade effect."""
    type: Literal["opacity"] = "opacity"
    value: float = Field(..., ge=0.0, le=1.0, description="Target opacity (0-1)")
    fade_direction: Optional[str] = Field(default=None, description="Optional: top, bottom, left, right for fade")


class InvertEffect(BaseModel):
    """Color inversion effect."""
    type: Literal["invert"] = "invert"
    amount: float = Field(default=1.0, ge=0.0, le=1.0, description="Inversion amount (0=none, 1=full)")


class SepiaEffect(BaseModel):
    """Sepia tone effect."""
    type: Literal["sepia"] = "sepia"
    amount: float = Field(default=1.0, ge=0.0, le=1.0, description="Sepia amount (0=color, 1=full sepia)")


class GrayscaleEffect(BaseModel):
    """Grayscale/desaturation effect."""
    type: Literal["grayscale"] = "grayscale"
    amount: float = Field(default=1.0, ge=0.0, le=1.0, description="Grayscale amount (0=color, 1=full grayscale)")


# Union of all effect types
EffectConfig = (
    ShadowEffect | GlowEffect | BlurEffect | HighlightEffect |
    VignetteEffect | OpacityEffect | InvertEffect | SepiaEffect | GrayscaleEffect
)


class LayerEffect(BaseModel):
    """A single effect applied to a layer."""
    effect_id: str = Field(default_factory=lambda: "eff_" + str(__import__('uuid').uuid4().hex[:8]))
    effect_config: EffectConfig = Field(..., description="Effect configuration")
    enabled: bool = Field(default=True, description="Whether effect is enabled")
    order: int = Field(default=0, description="Effect order (lower executes first)")
    
    class Config:
        arbitrary_types_allowed = True


class EffectStack(BaseModel):
    """Stack of effects to apply to a layer."""
    effects: List[LayerEffect] = Field(default_factory=list, description="Ordered list of effects")
    
    def add_effect(self, effect: LayerEffect) -> None:
        """Add effect to stack (auto-sorts by order)."""
        self.effects.append(effect)
        self.effects.sort(key=lambda e: e.order)
    
    def remove_effect(self, effect_id: str) -> bool:
        """Remove effect by ID."""
        initial_len = len(self.effects)
        self.effects = [e for e in self.effects if e.effect_id != effect_id]
        return len(self.effects) < initial_len
    
    def get_enabled_effects(self) -> List[LayerEffect]:
        """Get only enabled effects in order."""
        return [e for e in self.effects if e.enabled]


class EffectPreset(BaseModel):
    """Pre-defined effect preset for common use cases."""
    name: str = Field(..., description="Preset name")
    description: str = Field(default="", description="Preset description")
    effects: List[EffectConfig] = Field(..., description="List of effects in preset")


# Common effect presets
EFFECT_PRESETS = {
    "soft-shadow": EffectPreset(
        name="soft-shadow",
        description="Soft drop shadow for depth",
        effects=[
            ShadowEffect(
                mode="drop",
                x_offset=2,
                y_offset=4,
                blur_radius=8,
                color="#000000",
                opacity=0.15
            )
        ]
    ),
    "neon-glow": EffectPreset(
        name="neon-glow",
        description="Bright neon glow effect",
        effects=[
            GlowEffect(
                mode="outer",
                blur_radius=15,
                color="#FF00FF",
                opacity=0.8
            )
        ]
    ),
    "subtle-blur": EffectPreset(
        name="subtle-blur",
        description="Slight gaussian blur",
        effects=[
            BlurEffect(
                mode="gaussian",
                radius=2
            )
        ]
    ),
    "dark-vignette": EffectPreset(
        name="dark-vignette",
        description="Dark edges focusing attention",
        effects=[
            VignetteEffect(
                darkness=0.6,
                radius=0.7
            )
        ]
    ),
    "vintage": EffectPreset(
        name="vintage",
        description="Vintage sepia tone",
        effects=[
            SepiaEffect(amount=0.6),
            VignetteEffect(darkness=0.3, radius=0.8)
        ]
    ),
    "grayscale-dramatic": EffectPreset(
        name="grayscale-dramatic",
        description="Full grayscale with vignette",
        effects=[
            GrayscaleEffect(amount=1.0),
            VignetteEffect(darkness=0.5, radius=0.75)
        ]
    ),
    "elevated": EffectPreset(
        name="elevated",
        description="Elevated/lifted look with soft shadow and slight invert",
        effects=[
            ShadowEffect(mode="drop", x_offset=3, y_offset=5, blur_radius=10, opacity=0.2),
            OpacityEffect(value=0.98)
        ]
    ),
    "bold-highlight": EffectPreset(
        name="bold-highlight",
        description="Bold color highlight overlay",
        effects=[
            HighlightEffect(color="#FFFF00", opacity=0.4, mode="screen")
        ]
    ),
}


class EffectEngine:
    """Engine for applying effects to layers/images."""
    
    @staticmethod
    def apply_shadow(image_array, shadow: ShadowEffect) -> bytes:
        """Apply shadow effect to image."""
        try:
            from PIL import Image, ImageFilter, ImageDraw, ImageChops
            import numpy as np
            
            # Convert to PIL Image if needed
            if isinstance(image_array, bytes):
                import io
                img = Image.open(io.BytesIO(image_array))
            else:
                img = image_array
            
            # Create shadow layer
            shadow_img = Image.new("RGBA", img.size, (0, 0, 0, 0))
            
            # Parse shadow color
            r, g, b = int(shadow.color[1:3], 16), int(shadow.color[3:5], 16), int(shadow.color[5:7], 16)
            shadow_alpha = int(shadow.opacity * 255)
            
            # Create shadow effect
            if shadow.blur_radius > 0:
                shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=shadow.blur_radius))
            
            # Return as bytes (real implementation would composite)
            import io
            output = io.BytesIO()
            img.save(output, format="PNG")
            return output.getvalue()
        except ImportError:
            # PIL not available, return original
            return image_array if isinstance(image_array, bytes) else b""
    
    @staticmethod
    def apply_glow(image_array, glow: GlowEffect) -> bytes:
        """Apply glow effect to image."""
        try:
            from PIL import Image, ImageFilter
            import io
            
            if isinstance(image_array, bytes):
                img = Image.open(io.BytesIO(image_array))
            else:
                img = image_array
            
            # Create glow layer by blurring
            if glow.blur_radius > 0:
                glow_layer = img.filter(ImageFilter.GaussianBlur(radius=glow.blur_radius))
                
                # Composite glow over original
                img = Image.blend(img, glow_layer, glow.opacity)
            
            # Return as bytes
            output = io.BytesIO()
            img.save(output, format="PNG")
            return output.getvalue()
        except ImportError:
            return image_array if isinstance(image_array, bytes) else b""
    
    @staticmethod
    def apply_blur(image_array, blur: BlurEffect) -> bytes:
        """Apply blur effect to image."""
        try:
            from PIL import Image, ImageFilter
            import io
            
            if isinstance(image_array, bytes):
                img = Image.open(io.BytesIO(image_array))
            else:
                img = image_array
            
            # Apply blur based on mode
            if blur.mode == "gaussian":
                img = img.filter(ImageFilter.GaussianBlur(radius=blur.radius))
            elif blur.mode == "motion":
                # Motion blur (simplified)
                img = img.filter(ImageFilter.GaussianBlur(radius=blur.radius))
            elif blur.mode == "zoom":
                img = img.filter(ImageFilter.GaussianBlur(radius=blur.radius))
            
            output = io.BytesIO()
            img.save(output, format="PNG")
            return output.getvalue()
        except ImportError:
            return image_array if isinstance(image_array, bytes) else b""
    
    @staticmethod
    def apply_grayscale(image_array, gray: GrayscaleEffect) -> bytes:
        """Apply grayscale effect to image."""
        try:
            from PIL import Image, ImageOps
            import io
            
            if isinstance(image_array, bytes):
                img = Image.open(io.BytesIO(image_array))
            else:
                img = image_array
            
            # Convert to grayscale
            gray_img = ImageOps.grayscale(img)
            
            # Blend based on amount
            if gray.amount < 1.0:
                img = Image.blend(img.convert("RGB"), gray_img.convert("RGB"), gray.amount)
            else:
                img = gray_img.convert("RGB")
            
            output = io.BytesIO()
            img.save(output, format="PNG")
            return output.getvalue()
        except ImportError:
            return image_array if isinstance(image_array, bytes) else b""
    
    @staticmethod
    def apply_sepia(image_array, sepia: SepiaEffect) -> bytes:
        """Apply sepia tone effect to image."""
        try:
            from PIL import Image, ImageOps
            import io
            import numpy as np
            
            if isinstance(image_array, bytes):
                img = Image.open(io.BytesIO(image_array))
            else:
                img = image_array
            
            # Sepia matrix
            img_arr = np.array(img.convert("RGB"), dtype=np.float32)
            sepia_matrix = np.array([
                [0.393, 0.769, 0.189],
                [0.349, 0.686, 0.168],
                [0.272, 0.534, 0.131]
            ])
            sepia_arr = img_arr @ sepia_matrix.T
            sepia_arr = np.clip(sepia_arr, 0, 255).astype(np.uint8)
            
            sepia_img = Image.fromarray(sepia_arr)
            
            # Blend
            if sepia.amount < 1.0:
                img = Image.blend(img.convert("RGB"), sepia_img, sepia.amount)
            else:
                img = sepia_img
            
            output = io.BytesIO()
            img.save(output, format="PNG")
            return output.getvalue()
        except (ImportError, Exception):
            return image_array if isinstance(image_array, bytes) else b""
    
    @staticmethod
    def apply_effect_stack(image_array, effect_stack: EffectStack) -> bytes:
        """Apply a stack of effects in order."""
        result = image_array
        
        for effect in effect_stack.get_enabled_effects():
            config = effect.effect_config
            
            if isinstance(config, ShadowEffect):
                result = EffectEngine.apply_shadow(result, config)
            elif isinstance(config, GlowEffect):
                result = EffectEngine.apply_glow(result, config)
            elif isinstance(config, BlurEffect):
                result = EffectEngine.apply_blur(result, config)
            elif isinstance(config, GrayscaleEffect):
                result = EffectEngine.apply_grayscale(result, config)
            elif isinstance(config, SepiaEffect):
                result = EffectEngine.apply_sepia(result, config)
            # Other effects would be implemented similarly
        
        return result
    
    @staticmethod
    def get_preset(preset_name: str) -> Optional[EffectPreset]:
        """Get effect preset by name."""
        return EFFECT_PRESETS.get(preset_name)
    
    @staticmethod
    def list_presets() -> dict:
        """List all available effect presets."""
        return {
            name: {
                "description": preset.description,
                "effects": [e.type for e in preset.effects]
            }
            for name, preset in EFFECT_PRESETS.items()
        }
