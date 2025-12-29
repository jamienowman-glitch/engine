"""Auto-crop intelligence: smart cropping for different aspect ratios."""

from __future__ import annotations
from typing import Literal, Optional, Tuple, List
from pydantic import BaseModel, Field, validator
from dataclasses import dataclass


class FocalPoint(BaseModel):
    """Defines a focal point for intelligent cropping."""
    x: float = Field(..., ge=0.0, le=1.0, description="Normalized X coordinate (0-1)")
    y: float = Field(..., ge=0.0, le=1.0, description="Normalized Y coordinate (0-1)")
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="Importance weight (0-1)")
    
    @validator("x", "y", "weight")
    def validate_range(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError("Values must be between 0 and 1")
        return v


class AspectRatioConfig(BaseModel):
    """Configuration for cropping to a specific aspect ratio."""
    aspect_ratio: str = Field(..., description='Aspect ratio as "W:H", e.g., "16:9", "1:1", "4:3"')
    width: Optional[int] = Field(default=None, description="Target width in pixels (optional)")
    height: Optional[int] = Field(default=None, description="Target height in pixels (optional)")
    preserve_focal_point: bool = Field(default=True, description="Keep focal point centered in crop")
    
    @validator("aspect_ratio")
    def validate_ratio(cls, v):
        """Validate aspect ratio format (W:H)."""
        parts = v.split(":")
        if len(parts) != 2:
            raise ValueError("Aspect ratio must be in 'W:H' format, e.g., '16:9'")
        try:
            w, h = float(parts[0]), float(parts[1])
            if w <= 0 or h <= 0:
                raise ValueError("Aspect ratio values must be positive")
        except ValueError as e:
            raise ValueError(f"Invalid aspect ratio: {e}")
        return v
    
    def get_ratio_value(self) -> float:
        """Get aspect ratio as W/H decimal."""
        parts = self.aspect_ratio.split(":")
        return float(parts[0]) / float(parts[1])


class CropBox(BaseModel):
    """Defines a crop region."""
    x: int = Field(..., ge=0, description="Left edge in pixels")
    y: int = Field(..., ge=0, description="Top edge in pixels")
    width: int = Field(..., gt=0, description="Width in pixels")
    height: int = Field(..., gt=0, description="Height in pixels")
    
    def aspect_ratio(self) -> float:
        """Calculate actual aspect ratio of this crop box."""
        return self.width / self.height


class AutoCropRequest(BaseModel):
    """Request to auto-crop a composition."""
    composition_id: Optional[str] = None
    aspect_ratio: str = Field(..., description='Target aspect ratio, e.g., "16:9", "1:1", "4:3"')
    preserve_focal_point: bool = Field(default=True, description="Keep focal point centered")
    focal_points: List[FocalPoint] = Field(default_factory=list, description="Optional focal points for smart cropping")
    max_iterations: int = Field(default=10, ge=1, le=100, description="Max iterations for focal point detection")
    

class AutoCropResponse(BaseModel):
    """Response with crop recommendation."""
    crop_box: CropBox = Field(..., description="Recommended crop region")
    focal_point_used: Optional[FocalPoint] = Field(default=None, description="Focal point that was optimized for")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of crop recommendation (0-1)")
    method_used: Literal["focal_point", "center", "edge_detection"] = Field(
        default="center",
        description="Method used to determine crop"
    )


@dataclass
class CropOptions:
    """Runtime options for cropping."""
    aspect_ratio: str
    source_width: int
    source_height: int
    focal_points: List[FocalPoint] = None
    preserve_focal_point: bool = True
    center_if_no_focal: bool = True
    
    def __post_init__(self):
        if self.focal_points is None:
            self.focal_points = []


class AutoCropEngine:
    """Engine for intelligent auto-cropping to various aspect ratios."""
    
    # Common aspect ratios for social media, print, and web
    PRESET_RATIOS = {
        # Social Media
        "instagram-square": "1:1",
        "instagram-portrait": "4:5",
        "instagram-landscape": "1.91:1",
        "instagram-story": "9:16",
        "facebook-cover": "16:9",
        "facebook-post": "1.2:1",
        "twitter-header": "3:1",
        "twitter-post": "1.91:1",
        "tiktok": "9:16",
        "youtube-thumbnail": "16:9",
        "youtube-banner": "16:9.25",
        
        # Print
        "postcard": "6:4",
        "business-card": "3.5:2",
        "flyer-half": "11:8.5",
        "flyer-full": "8.5:11",
        "poster-a3": "420:297",
        "poster-a2": "594:420",
        
        # Web
        "widescreen": "16:9",
        "ultrawide": "21:9",
        "cinema": "2.39:1",
        "square": "1:1",
        "tall": "9:16",
        
        # Video
        "4k": "16:9",
        "720p": "16:9",
        "mobile": "9:16",
    }
    
    @staticmethod
    def calculate_crop_box(
        source_width: int,
        source_height: int,
        target_ratio: float,
        focal_point: Optional[FocalPoint] = None
    ) -> CropBox:
        """
        Calculate optimal crop box for target aspect ratio.
        
        Strategy:
        1. If focal_point provided: center crop on it
        2. Otherwise: center crop on image center
        
        Args:
            source_width: Original image width
            source_height: Original image height
            target_ratio: Target aspect ratio (W/H)
            focal_point: Optional focal point to preserve
        
        Returns:
            CropBox with optimal crop coordinates
        """
        # Calculate crop dimensions
        source_ratio = source_width / source_height
        
        if source_ratio > target_ratio:
            # Source is wider -> crop width
            crop_height = source_height
            crop_width = int(crop_height * target_ratio)
        else:
            # Source is taller -> crop height
            crop_width = source_width
            crop_height = int(crop_width / target_ratio)
        
        # Determine crop position
        if focal_point:
            # Center on focal point
            focal_px_x = int(focal_point.x * source_width)
            focal_px_y = int(focal_point.y * source_height)
            
            crop_x = max(0, min(source_width - crop_width, focal_px_x - crop_width // 2))
            crop_y = max(0, min(source_height - crop_height, focal_px_y - crop_height // 2))
        else:
            # Center on image center
            crop_x = (source_width - crop_width) // 2
            crop_y = (source_height - crop_height) // 2
        
        return CropBox(x=crop_x, y=crop_y, width=crop_width, height=crop_height)
    
    @staticmethod
    def detect_focal_point(image_array) -> Optional[FocalPoint]:
        """
        Detect focal point using edge detection (Canny edge detection).
        Finds the region with highest content density.
        
        Requires numpy and opencv-python.
        Returns focal point at center of highest-energy region.
        """
        try:
            import cv2
            import numpy as np
            
            if isinstance(image_array, np.ndarray):
                img = image_array
            else:
                # Convert PIL Image to numpy array
                import numpy as np
                img = np.array(image_array)
            
            # Convert to grayscale if needed
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            else:
                gray = img
            
            # Detect edges
            edges = cv2.Canny(gray, 100, 200)
            
            # Find contours / connected components
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                # No edges detected, use center
                return FocalPoint(x=0.5, y=0.5, weight=0.5)
            
            # Find largest contour (assuming subject)
            largest = max(contours, key=cv2.contourArea)
            moments = cv2.moments(largest)
            
            if moments["m00"] > 0:
                cx = moments["m10"] / moments["m00"]
                cy = moments["m01"] / moments["m00"]
                
                h, w = gray.shape
                focal_x = cx / w
                focal_y = cy / h
                
                return FocalPoint(x=focal_x, y=focal_y, weight=0.8)
        except (ImportError, Exception):
            # OpenCV not available or detection failed
            return None
        
        return None
    
    @staticmethod
    def merge_focal_points(focal_points: List[FocalPoint]) -> Optional[FocalPoint]:
        """
        Merge multiple focal points into a weighted average.
        Used when multiple subjects are detected.
        """
        if not focal_points:
            return None
        
        total_weight = sum(fp.weight for fp in focal_points)
        if total_weight == 0:
            return None
        
        avg_x = sum(fp.x * fp.weight for fp in focal_points) / total_weight
        avg_y = sum(fp.y * fp.weight for fp in focal_points) / total_weight
        avg_weight = total_weight / len(focal_points)
        
        return FocalPoint(x=avg_x, y=avg_y, weight=min(avg_weight, 1.0))
    
    @staticmethod
    def get_crop_for_preset(
        preset_name: str,
        source_width: int,
        source_height: int,
        focal_point: Optional[FocalPoint] = None
    ) -> Optional[CropBox]:
        """
        Get crop box for a named preset (e.g., "instagram-square").
        """
        ratio_str = AutoCropEngine.PRESET_RATIOS.get(preset_name)
        if not ratio_str:
            return None
        
        # Parse ratio
        parts = ratio_str.split(":")
        target_ratio = float(parts[0]) / float(parts[1])
        
        return AutoCropEngine.calculate_crop_box(
            source_width=source_width,
            source_height=source_height,
            target_ratio=target_ratio,
            focal_point=focal_point
        )
