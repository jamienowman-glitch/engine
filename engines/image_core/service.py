from __future__ import annotations
import uuid
import io
import json
import hashlib
from typing import Optional, Dict, Tuple, List
from engines.media_v2.service import MediaService, get_media_service
from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest, DerivedArtifact
from engines.image_core.models import ImageComposition, ImageSelection
from engines.image_core.backend import ImageCoreBackend

class ImageCoreService:
    PRESETS = {
        # Web/General
        "web_small": {"format": "WEBP", "width": 640, "height": None, "quality": 75},
        "web_medium": {"format": "WEBP", "width": 1280, "height": None, "quality": 85},
        "web_large": {"format": "WEBP", "width": 2048, "height": None, "quality": 90},
        "original": {"format": "PNG", "width": None, "height": None, "quality": None},
        
        # Social Media - Feed/Posts
        "social_1080p": {"format": "PNG", "width": 1920, "height": 1080, "quality": None},
        "instagram_1080": {"format": "JPEG", "width": 1080, "height": 1080, "quality": 90},
        "instagram_story_1080x1920": {"format": "WEBP", "width": 1080, "height": 1920, "quality": 85},
        "twitter_card_1200x675": {"format": "JPEG", "width": 1200, "height": 675, "quality": 85},
        "linkedin_banner_1584x396": {"format": "JPEG", "width": 1584, "height": 396, "quality": 85},
        "facebook_cover_820x312": {"format": "JPEG", "width": 820, "height": 312, "quality": 85},
        "pinterest_pin_1000x1500": {"format": "JPEG", "width": 1000, "height": 1500, "quality": 85},
        
        # Social Media - Video/Short Form
        "tiktok_video_1080x1920": {"format": "WEBP", "width": 1080, "height": 1920, "quality": 80},
        "snapchat_story_1080x1920": {"format": "WEBP", "width": 1080, "height": 1920, "quality": 75},
        "youtube_thumbnail_1280x720": {"format": "JPEG", "width": 1280, "height": 720, "quality": 90},
        
        # Email & Web Content
        "email_header_600x200": {"format": "JPEG", "width": 600, "height": 200, "quality": 85},
        "email_body_600x400": {"format": "JPEG", "width": 600, "height": 400, "quality": 80},
        "newsletter_banner_640": {"format": "WEBP", "width": 640, "height": 360, "quality": 85},
        "web_og_image_1200x630": {"format": "JPEG", "width": 1200, "height": 630, "quality": 90},
        
        # E-Commerce
        "ecommerce_product_400x400": {"format": "PNG", "width": 400, "height": 400, "quality": None},
        "ecommerce_product_800x800": {"format": "PNG", "width": 800, "height": 800, "quality": None},
        "ecommerce_gallery_1200x1200": {"format": "JPEG", "width": 1200, "height": 1200, "quality": 95},
        
        # Icons & Avatars
        "avatar_64x64": {"format": "PNG", "width": 64, "height": 64, "quality": None},
        "avatar_128x128": {"format": "PNG", "width": 128, "height": 128, "quality": None},
        "icon_256x256": {"format": "PNG", "width": 256, "height": 256, "quality": None},
        "icon_512x512": {"format": "PNG", "width": 512, "height": 512, "quality": None},
        "thumbnail_200": {"format": "PNG", "width": 200, "height": 200, "quality": None},
        
        # Display & Screens
        "desktop_1920x1080": {"format": "WEBP", "width": 1920, "height": 1080, "quality": 90},
        "desktop_2560x1440": {"format": "WEBP", "width": 2560, "height": 1440, "quality": 92},
        "ultrawide_3440x1440": {"format": "WEBP", "width": 3440, "height": 1440, "quality": 85},
        "retina_display_2x": {"format": "WEBP", "width": 2048, "height": 1536, "quality": 95},
        "hero_1920x1080": {"format": "PNG", "width": 1920, "height": 1080, "quality": None},
        "mobile_small_640x360": {"format": "WEBP", "width": 640, "height": 360, "quality": 75},
        
        # Ads & Banners
        "google_ads_300x250": {"format": "JPEG", "width": 300, "height": 250, "quality": 85},
        "google_ads_728x90": {"format": "JPEG", "width": 728, "height": 90, "quality": 85},
        "facebook_ads_1200x628": {"format": "JPEG", "width": 1200, "height": 628, "quality": 85},
        "banner_970x250": {"format": "JPEG", "width": 970, "height": 250, "quality": 85},
        
        # Print Materials
        "print_postcard_4x6_300dpi": {"format": "JPEG", "width": 1200, "height": 1800, "quality": 95, "dpi": 300},
        "print_business_card_3_5x2_300dpi": {"format": "JPEG", "width": 1050, "height": 700, "quality": 95, "dpi": 300},
        "print_poster_18x24_300dpi": {"format": "JPEG", "width": 5400, "height": 7200, "quality": 95, "dpi": 300},
        "print_a4_300dpi": {"format": "JPEG", "width": 2480, "height": 3508, "quality": 95, "dpi": 300},
        "print_a3_300dpi": {"format": "JPEG", "width": 3508, "height": 4961, "quality": 95, "dpi": 300},
        "print_300dpi": {"format": "JPEG", "width": 3000, "height": 3000, "quality": 95},
        
        # Quick/Draft Versions
        "draft_preview_480": {"format": "WEBP", "width": 480, "height": None, "quality": 60},
        "draft_preview_720": {"format": "WEBP", "width": 720, "height": None, "quality": 70},
        
        # Archive/High-Quality
        "tiff_high_quality": {"format": "TIFF", "width": None, "height": None, "quality": None},
    }

    def __init__(self, media_service: Optional[MediaService] = None):
        self.media_service = media_service or get_media_service()
        self.backend = ImageCoreBackend(self.media_service)
        self._mask_cache: Dict[Tuple[str, str, str], DerivedArtifact] = {}

    def render_composition(self, comp: ImageComposition, parent_asset_id: Optional[str] = None, preset_id: Optional[str] = None) -> str:
        """
        Renders the composition and returns the Artifact ID of the result.
        Accepts an optional `preset_id` to export in a specific format/size (e.g., web/social/print presets).
        """
        if comp.width <= 0 or comp.height <= 0:
            raise ValueError("Composition width/height must be positive")
        if not comp.tenant_id or not comp.env:
            raise ValueError("Composition must include tenant_id and env")
        for layer in comp.layers:
            if not (0.0 <= layer.opacity <= 1.0):
                raise ValueError("Layer opacity must be between 0 and 1")

        pipeline_hash = self.backend.compute_pipeline_hash(comp)
        # Base render (PNG)
        png_bytes = self.backend.render(comp, pipeline_hash=pipeline_hash)
        blend_modes = sorted({layer.blend_mode for layer in comp.layers})

        out_bytes = png_bytes
        out_format = "PNG"

        # Apply preset transformation if requested
        if preset_id:
            preset = self.PRESETS.get(preset_id)
            if not preset:
                raise ValueError("Unknown preset_id")
            from PIL import Image
            img = Image.open(io.BytesIO(png_bytes))
            target_w = preset.get("width")
            target_h = preset.get("height")
            if target_w or target_h:
                if not target_h:
                    ratio = target_w / img.width
                    target_h = max(1, int(img.height * ratio))
                img = img.resize((int(target_w), int(target_h)), Image.Resampling.LANCZOS)
            out_format = preset["format"]
            out_io = io.BytesIO()
            save_kwargs = {}
            if preset.get("quality"):
                save_kwargs["quality"] = preset["quality"]
            if preset.get("dpi"):
                save_kwargs["dpi"] = (preset["dpi"], preset["dpi"])
            # Convert modes for formats that don't support alpha
            if out_format.upper() in {"JPEG", "JPG"} and img.mode in ("RGBA", "LA"):
                img = img.convert("RGB")
            img.save(out_io, format=out_format, **save_kwargs)
            out_bytes = out_io.getvalue()

        ext = out_format.lower()
        filename = f"image_render_{uuid.uuid4().hex[:8]}.{ext}"

        up_req = MediaUploadRequest(
            tenant_id=comp.tenant_id,
            env=comp.env,
            kind="image",
            source_uri="pending",
            tags=["generated", "image_core", "composition"],
            meta={"pipeline_hash": pipeline_hash, "blend_modes": blend_modes, "preset_id": preset_id, "format": out_format},
        )

        new_asset = self.media_service.register_upload(up_req, filename, out_bytes)

        pid = parent_asset_id or new_asset.id

        art_meta = {
            "width": comp.width,
            "height": comp.height,
            "layers_count": len(comp.layers),
            "blend_modes": blend_modes,
            "pipeline_hash": pipeline_hash,
            "background_color": comp.background_color,
            "preset_id": preset_id,
            "format": out_format,
        }

        art = self.media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id=comp.tenant_id,
                env=comp.env,
                parent_asset_id=pid,
                kind="image_render",
                uri=new_asset.source_uri,
                meta=art_meta,
            )
        )

        return art.id

    def batch_render(self, comp: ImageComposition, preset_ids: List[str], parent_asset_id: Optional[str] = None) -> Dict[str, str]:
        """
        Render a composition to multiple presets in a single pass.
        Reduces redundant rendering by using cached pipeline.
        
        Args:
            comp: ImageComposition to render
            preset_ids: List of preset IDs to export
            parent_asset_id: Optional parent asset ID
            
        Returns:
            Dict mapping preset_id → artifact_id
        """
        if not preset_ids:
            raise ValueError("preset_ids cannot be empty")
        if len(preset_ids) > 20:
            raise ValueError("Too many presets (max 20)")
        
        # Validate composition once
        if comp.width <= 0 or comp.height <= 0:
            raise ValueError("Composition width/height must be positive")
        if not comp.tenant_id or not comp.env:
            raise ValueError("Composition must include tenant_id and env")
        for layer in comp.layers:
            if not (0.0 <= layer.opacity <= 1.0):
                raise ValueError("Layer opacity must be between 0 and 1")
        
        # Single render pass
        pipeline_hash = self.backend.compute_pipeline_hash(comp)
        png_bytes = self.backend.render(comp, pipeline_hash=pipeline_hash)
        blend_modes = sorted({layer.blend_mode for layer in comp.layers})
        
        results: Dict[str, str] = {}
        
        for preset_id in preset_ids:
            try:
                preset = self.PRESETS.get(preset_id)
                if not preset:
                    continue  # Skip unknown presets
                
                from PIL import Image
                img = Image.open(io.BytesIO(png_bytes))
                target_w = preset.get("width")
                target_h = preset.get("height")
                if target_w or target_h:
                    if not target_h:
                        ratio = target_w / img.width
                        target_h = max(1, int(img.height * ratio))
                    img = img.resize((int(target_w), int(target_h)), Image.Resampling.LANCZOS)
                
                out_format = preset["format"]
                out_io = io.BytesIO()
                save_kwargs = {}
                if preset.get("quality"):
                    save_kwargs["quality"] = preset["quality"]
                if preset.get("dpi"):
                    save_kwargs["dpi"] = (preset["dpi"], preset["dpi"])
                
                # Convert modes for formats that don't support alpha
                if out_format.upper() in {"JPEG", "JPG"} and img.mode in ("RGBA", "LA"):
                    img = img.convert("RGB")
                img.save(out_io, format=out_format, **save_kwargs)
                out_bytes = out_io.getvalue()
                
                ext = out_format.lower()
                filename = f"image_render_{preset_id}_{uuid.uuid4().hex[:8]}.{ext}"
                
                up_req = MediaUploadRequest(
                    tenant_id=comp.tenant_id,
                    env=comp.env,
                    kind="image",
                    source_uri="pending",
                    tags=["generated", "image_core", "composition", f"preset_{preset_id}"],
                    meta={"pipeline_hash": pipeline_hash, "blend_modes": blend_modes, "preset_id": preset_id, "format": out_format},
                )
                
                new_asset = self.media_service.register_upload(up_req, filename, out_bytes)
                pid = parent_asset_id or new_asset.id
                
                art_meta = {
                    "width": comp.width,
                    "height": comp.height,
                    "layers_count": len(comp.layers),
                    "blend_modes": blend_modes,
                    "pipeline_hash": pipeline_hash,
                    "background_color": comp.background_color,
                    "preset_id": preset_id,
                    "format": out_format,
                }
                
                art = self.media_service.register_artifact(
                    ArtifactCreateRequest(
                        tenant_id=comp.tenant_id,
                        env=comp.env,
                        parent_asset_id=pid,
                        kind="image_render",
                        uri=new_asset.source_uri,
                        meta=art_meta,
                    )
                )
                results[preset_id] = art.id
                
            except Exception as e:
                print(f"Warning: batch_render failed for preset {preset_id}: {e}")
                continue
        
        return results

    def _selection_hash(self, selection: ImageSelection, width: int, height: int) -> str:
        normalized = self._normalize_value(selection.model_dump())
        normalized["width"] = width
        normalized["height"] = height
        serialized = json.dumps(normalized, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def _normalize_value(self, value):
        if isinstance(value, dict):
            return {k: self._normalize_value(value[k]) for k in sorted(value)}
        if isinstance(value, list):
            return [self._normalize_value(v) for v in value]
        if isinstance(value, tuple):
            return [self._normalize_value(v) for v in value]
        return value

    def generate_mask(self, selection: ImageSelection, width: int, height: int, tenant_id: str, env: str) -> str:
        """
        Generates a mask, saves it as an artifact, and returns the artifact ID.
        """
        if not tenant_id or not env:
            raise ValueError("tenant_id and env are required to generate a mask")
        if width <= 0 or height <= 0:
            raise ValueError("Mask width/height must be positive")

        # Clamp/validate feather and stroke widths
        max_dim = max(width, height)
        if selection.feather_radius < 0 or selection.feather_radius > max_dim / 2:
            raise ValueError("Selection feather_radius out of allowed range")
        for s in selection.strokes or []:
            if s.width <= 0 or s.width > max_dim:
                raise ValueError("Brush stroke width out of allowed range")

        selection_hash = self._selection_hash(selection, width, height)
        cache_key = (tenant_id, env, selection_hash)
        cached = self._mask_cache.get(cache_key)
        if cached:
            return cached.id

        from engines.image_core.selections import rasterize_selection
        mask_img = rasterize_selection(selection, width, height)
        
        out_io = io.BytesIO()
        mask_img.save(out_io, format="PNG")
        content = out_io.getvalue()
        
        filename = f"mask_{uuid.uuid4().hex[:8]}.png"
        
        up_req = MediaUploadRequest(
            tenant_id=tenant_id,
            env=env,
            kind="image",
            source_uri="pending",
            tags=["generated", "image_core", "mask"]
        )
        
        new_asset = self.media_service.register_upload(up_req, filename, content)
        
        art = self.media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id=tenant_id,
                env=env,
                parent_asset_id=new_asset.id,
                kind="mask", # Re-uses existing mask kind? Or image_render? "mask" exists in v2.
                uri=new_asset.source_uri,
                meta={
                    "width": width,
                    "height": height,
                    "feather_radius": selection.feather_radius,
                    "selection_hash": selection_hash,
                    "mask_type": selection.type,
                    "points_count": len(selection.points),
                    "strokes_count": len(selection.strokes),
                }
            )
        )
        self._mask_cache[cache_key] = art
        return art.id

    def calculate_auto_crop(
        self,
        source_width: int,
        source_height: int,
        aspect_ratio: str,
        focal_point: Optional[tuple] = None
    ) -> Dict:
        """
        Calculate crop box for a target aspect ratio.
        
        Args:
            source_width: Original image width
            source_height: Original image height
            aspect_ratio: Target ratio as "W:H" (e.g., "16:9", "1:1")
            focal_point: Optional (x, y) tuple with normalized coords (0-1)
        
        Returns:
            Dict with crop_box (x, y, width, height), confidence, method
        """
        from engines.image_core.auto_crop import AutoCropEngine, FocalPoint
        
        # Parse aspect ratio
        try:
            parts = aspect_ratio.split(":")
            target_ratio = float(parts[0]) / float(parts[1])
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid aspect ratio '{aspect_ratio}': {e}")
        
        # Convert focal point if provided
        focal_fp = None
        if focal_point:
            focal_fp = FocalPoint(x=focal_point[0], y=focal_point[1])
        
        # Calculate crop
        crop_box = AutoCropEngine.calculate_crop_box(
            source_width=source_width,
            source_height=source_height,
            target_ratio=target_ratio,
            focal_point=focal_fp
        )
        
        return {
            "crop_box": {
                "x": crop_box.x,
                "y": crop_box.y,
                "width": crop_box.width,
                "height": crop_box.height,
                "aspect_ratio": f"{crop_box.width}:{crop_box.height}"
            },
            "focal_point_used": focal_point if focal_fp else None,
            "confidence": 0.85 if focal_fp else 0.70,
            "method": "focal_point" if focal_fp else "center"
        }
    
    def get_crop_for_preset(
        self,
        preset_name: str,
        source_width: int,
        source_height: int,
        focal_point: Optional[tuple] = None
    ) -> Optional[Dict]:
        """
        Get crop box for a named preset (e.g., "instagram-square").
        
        Args:
            preset_name: Preset identifier (e.g., "instagram-square")
            source_width: Original image width
            source_height: Original image height
            focal_point: Optional (x, y) focal point
        
        Returns:
            Dict with crop_box or None if preset not found
        """
        from engines.image_core.auto_crop import AutoCropEngine, FocalPoint
        
        # Convert focal point if provided
        focal_fp = None
        if focal_point:
            focal_fp = FocalPoint(x=focal_point[0], y=focal_point[1])
        
        # Get crop for preset
        crop_box = AutoCropEngine.get_crop_for_preset(
            preset_name=preset_name,
            source_width=source_width,
            source_height=source_height,
            focal_point=focal_fp
        )
        
        if not crop_box:
            return None
        
        return {
            "crop_box": {
                "x": crop_box.x,
                "y": crop_box.y,
                "width": crop_box.width,
                "height": crop_box.height,
            },
            "focal_point_used": focal_point if focal_fp else None,
            "confidence": 0.85 if focal_fp else 0.70,
            "method": "focal_point" if focal_fp else "center",
            "preset": preset_name
        }

_default_service: Optional[ImageCoreService] = None

def get_image_core_service() -> ImageCoreService:
    global _default_service
    if _default_service is None:
        _default_service = ImageCoreService()
    return _default_service
