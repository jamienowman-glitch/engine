from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

# Try to import fontTools for variable font support (optional enhancement)
# For V1 we might skip complex variation instancing if PIL doesn't support it natively with specific params.
# PIL 10+ supports variations in ImageFont.truetype(..., layout_engine=ImageFont.Layout.RAQM) with libraqm?
# Or we just use standard weight if mapped to a static file.
# For this task, we will try to use a static font or a standard TTF.

from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest
from engines.media_v2.service import get_media_service, MediaService
from engines.video_text.models import TextRenderRequest, TextRenderResponse


class VideoTextService:
    def __init__(self, media_service: Optional[MediaService] = None):
        self.media_service = media_service or get_media_service()

    def _resolve_font_path(self, font_family: str) -> str:
        # Check if asked for Roboto Flex (default or explicit)
        if font_family in ("Inter", "Roboto Flex", "RobotoFlex"):
             # Try to find it in engines/design/fonts relative paths
             # Based on design/fonts/roboto_flex.json: "fonts/roboto-flex/RobotoFlex-VariableFont.ttf"
             # We check relative to engines/design
             base_design = Path(__file__).parent.parent.parent / "engines/design"
             
             candidates = [
                 base_design / "fonts/roboto-flex/RobotoFlex-VariableFont.ttf",
                 base_design / "fonts/RobotoFlex-VariableFont.ttf",
                 # Also check system locations for it
                 "/Library/Fonts/RobotoFlex-VariableFont.ttf",
                 "/usr/share/fonts/truetype/RobotoFlex-VariableFont.ttf"
             ]
             for c in candidates:
                 if c.exists():
                     return str(c)

        # Standard Fallbacks
        candidates = [
            "/Library/Fonts/Arial.ttf", # Mac
            "/System/Library/Fonts/Helvetica.ttc", # Mac fallback
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", # Linux
            "Arial.ttf" # PIL search
        ]
        
        for c in candidates:
            if Path(c).exists():
                return str(c)
        
        return "Arial"

    def render_text_image(self, req: TextRenderRequest) -> TextRenderResponse:
        text = req.text
        if not text:
            raise ValueError("Text cannot be empty")

        font_path = self._resolve_font_path(req.font_family)
        size = req.font_size_px
        
        try:
            # Note: PIL's handling of VariationSettings is limited. 
            # We would typically need to use fontTools.varLib.mutator to instantiate a TTF at specific axes 
            # and save to temp file, then load that.
            # For V1 "Muscle", we will skip variable axes application unless critical.
            # We just load the font at the requested size.
            font = ImageFont.truetype(font_path, size)
        except OSError:
            # Fallback to default if load fails
            font = ImageFont.load_default()
            # Default font size is fixed/small, can't scale easily without blur.
            # This is a fallback path.
            
        # Determine size
        # ImageDraw.textbbox (Left, Top, Right, Bottom)
        dummy_img = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Add some padding?
        padding = 20
        final_width = (req.width or text_width) + padding * 2
        final_height = (req.height or text_height) + padding * 2
        
        # Create Image
        img = Image.new("RGBA", (int(final_width), int(final_height)), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Position (centered if fixed size, or just padded)
        x = (final_width - text_width) / 2
        y = (final_height - text_height) / 2
        # Adjust for bbox offset
        x -= bbox[0]
        y -= bbox[1]
        
        draw.text((x, y), text, font=font, fill=req.color_hex)
        
        # Save to temp
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            img.save(tmp.name)
            out_path = tmp.name
            
        # Register
        upload_req = MediaUploadRequest(
            tenant_id=req.tenant_id,
            env=req.env,
            user_id=req.user_id,
            kind="image",
            source_uri=str(out_path),
            tags=["text_render", f"font_{req.font_family}"]
        )
        asset = self.media_service.register_remote(upload_req)
        
        return TextRenderResponse(
            asset_id=asset.id,
            uri=str(out_path),
            width=int(final_width),
            height=int(final_height),
            meta={
                "font_family": req.font_family,
                "text_length": len(text)
            }
        )

_default_service: Optional[VideoTextService] = None

def get_video_text_service() -> VideoTextService:
    global _default_service
    if _default_service is None:
        _default_service = VideoTextService()
    return _default_service
