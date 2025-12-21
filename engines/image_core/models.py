from __future__ import annotations
from typing import List, Optional, Literal, Tuple, Any, Dict
from pydantic import BaseModel, Field, validator, root_validator
import uuid

def _uuid() -> str:
    return uuid.uuid4().hex

BlendMode = Literal["normal", "multiply", "screen", "overlay", "darken", "lighten", "add"]
FilterMode = Literal["none", "blur", "sharpen"]

class ImageAdjustment(BaseModel):
    exposure: float = 0.0 # -1.0 to 1.0 (approx stops logic or strength)
    contrast: float = 1.0 # 1.0 is normal
    saturation: float = 1.0 # 1.0 is normal
    brightness: float = 1.0 # 1.0 is normal
    sharpness: float = 1.0 # 1.0 is normal
    gamma: float = 1.0 # 1.0 is normal

class BrushStroke(BaseModel):
    points: List[Tuple[int, int]]
    width: int = 10
    opacity: float = 1.0

    @validator("width")
    def width_positive(cls, value):
        if value <= 0:
            raise ValueError("Brush stroke width must be positive")
        return value

    @validator("opacity")
    def opacity_range(cls, value):
        if not 0.0 <= value <= 1.0:
            raise ValueError("Brush stroke opacity must be between 0 and 1")
        return value

class ImageSelection(BaseModel):
    type: Literal["polygon", "brush"] = "polygon"
    points: List[Tuple[int, int]] = Field(default_factory=list) # For polygon
    strokes: List[BrushStroke] = Field(default_factory=list) # For brush
    feather_radius: float = 0.0
    inverted: bool = False

    @validator("points", each_item=True)
    def ensure_point_pair(cls, point):
        if len(point) != 2:
            raise ValueError("Selection points must be 2-dimensional")
        return point

    @root_validator(skip_on_failure=True)
    def validate_selection(cls, values):
        sel_type = values.get("type")
        points = values.get("points") or []
        strokes = values.get("strokes") or []
        if sel_type == "polygon" and len(points) < 3:
            raise ValueError("Polygon selection requires at least 3 points")
        if sel_type == "brush" and not strokes:
            raise ValueError("Brush selection requires at least one stroke")
        return values

    @validator("feather_radius")
    def feather_non_negative(cls, value):
        if value < 0:
            raise ValueError("Feather radius must be non-negative")
        return value

class ImageLayer(BaseModel):
    id: str = Field(default_factory=_uuid)
    name: str = "Layer"
    
    # Source
    asset_id: Optional[str] = None # Reference to a media asset (image)
    color: Optional[str] = None # Hex string e.g. "#FF0000", if asset_id is None
    
    # Masking
    mask: Optional[ImageSelection] = None
    mask_artifact_id: Optional[str] = None
    
    # Text Content
    text: Optional[str] = None
    text_font: str = "Inter"
    text_preset: str = "regular"
    text_size: int = 100
    text_color: str = "#FFFFFF"
    text_tracking: int = 0
    text_variation_settings: Dict[str, float] = Field(default_factory=dict)
    
    # Vector Content
    # We must import VectorScene carefully to avoid circular deps if models import each other.
    # But since VectorScene is pydantic, we can use forward ref or just 'Any' / 'Dict' if needed, 
    # but models usually fine if no runtime loop.
    # Actually ImageCore depends on VectorCore is fine.
    # We need to import VectorScene at top or use string forward ref if circular.
    vector_scene: Optional[Any] = None # Avoiding direct import in models.py if not strictly needed for validation?
    # Pydantic supports Any. Better: use 'dict' and parse in backend?
    # Or proper import. Let's try proper import.
    
    # Transform
    x: int = 0
    y: int = 0
    width: Optional[int] = None # If None, use original
    height: Optional[int] = None
    rotation: float = 0.0
    scale: float = 1.0
    
    opacity: float = 1.0
    blend_mode: BlendMode = "normal"
    filter_mode: FilterMode = "none"
    filter_strength: float = 1.0
    
    adjustments: ImageAdjustment = Field(default_factory=ImageAdjustment)
    
class ImageComposition(BaseModel):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    env: str
    
    width: int = 1920
    height: int = 1080
    background_color: str = "#00000000" # Transparent black default
    
    layers: List[ImageLayer] = Field(default_factory=list)

ImageLayer.model_rebuild()
ImageComposition.model_rebuild()
