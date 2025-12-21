from PIL import Image, ImageDraw, ImageFilter
from engines.image_core.models import ImageSelection

def rasterize_selection(selection: ImageSelection, width: int, height: int) -> Image.Image:
    """
    Creates an L-mode (grayscale) image representing the mask.
    White (255) = Selected/Opaque, Black (0) = Unselected/Transparent.
    """
    # Create black canvas
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    
    if selection.type == "polygon":
        if selection.points:
            draw.polygon(selection.points, fill=255, outline=None)
            
    elif selection.type == "brush":
        for stroke in selection.strokes:
            if len(stroke.points) > 1:
                fill = max(0, min(255, int(255 * stroke.opacity)))
                draw.line(stroke.points, fill=fill, width=stroke.width, joint="curve")
                # Draw circles at start/end for rounded caps simulation if needed, 
                # PIL line caps are flat/box by default.
                # For basic brush, line is okay.
                
    # Invert if needed
    if selection.inverted:
        # 0->255, 255->0
        # ImageOps.invert requires L or RGB.
        from PIL import ImageOps
        mask = ImageOps.invert(mask)
        
    # Feathering
    if selection.feather_radius > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(radius=selection.feather_radius))
        
    return mask
