from __future__ import annotations
import uuid
import io
import json
import hashlib
import os
from copy import deepcopy
from typing import Optional, Dict, Tuple, List, Any, Protocol, Literal
from engines.media_v2.service import MediaService, get_media_service
from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest, DerivedArtifact
from engines.image_core.models import ImageAdjustment, ImageLayer, ImageComposition, ImageSelection
from engines.image_core.backend import ImageCoreBackend
from engines.typography_core.models import TextLayoutRequest
from engines.typography_core.renderer import TextLayoutMetadata
from engines.typography_core.service import TypographyService
from PIL import Image, ImageDraw, ImageFilter
from PIL import ImageOps

DEFAULT_NO_CODE_MAN_RECIPE_ID = "no_code_man_v1"

def _compute_safe_title_box(width: int, height: int) -> Dict[str, float]:
    safe_width = int(width * 0.9)
    safe_height = int(height * 0.8)
    horizontal_margin = (width - safe_width) // 2
    vertical_margin = (height - safe_height) // 2
    return {
        "width": safe_width,
        "height": safe_height,
        "x": horizontal_margin,
        "y": vertical_margin,
        "horizontal_margin_pct": 0.05,
        "vertical_margin_pct": 0.1,
        "width_pct": 0.9,
        "height_pct": 0.8,
        "centered": True,
    }

def _build_thumbnail_preset(preset_id: str, width: int, height: int, aspect_ratio: str) -> Dict[str, Any]:
    return {
        "preset_id": preset_id,
        "width": width,
        "height": height,
        "aspect_ratio": aspect_ratio,
        "format": "PNG",
        "quality": 90,
        "recipe_id": DEFAULT_NO_CODE_MAN_RECIPE_ID,
        "safe_title_box": _compute_safe_title_box(width, height),
    }

_SOCIAL_THUMBNAIL_PRESET_SPECS = {
    "youtube_thumb_16_9": (1280, 720, "16:9"),
    "social_vertical_story_9_16": (1080, 1920, "9:16"),
    "social_square_1_1": (1080, 1080, "1:1"),
    "social_4_3_comfort": (1440, 1080, "4:3"),
}

_SOCIAL_THUMBNAIL_PRESETS = {
    preset_id: _build_thumbnail_preset(preset_id, *spec)
    for preset_id, spec in _SOCIAL_THUMBNAIL_PRESET_SPECS.items()
}


class SubjectDetectionError(Exception):
    """Base class for subject detector failures."""
    pass


class SubjectDetectorUnavailable(SubjectDetectionError):
    """Raised when the real detector backend cannot be initialized or is missing."""
    pass


class SubjectDetectionFailure(SubjectDetectionError):
    """Raised when the detector runs but no subjects are found."""
    pass


class SubjectDetector:
    """Real subject detector wrapper (OpenCV Haar cascade)."""

    def __init__(self):
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            raise SubjectDetectorUnavailable(
                "OpenCV and NumPy are required for subject detection"
            ) from exc

        cascade_root = getattr(cv2.data, "haarcascades", None)
        cascade_path = (
            os.path.join(cascade_root, "haarcascade_frontalface_default.xml")
            if cascade_root
            else None
        )
        if not cascade_path or not os.path.exists(cascade_path):
            raise SubjectDetectorUnavailable("Haar cascade file is missing from OpenCV data")

        classifier = cv2.CascadeClassifier(cascade_path)
        if classifier.empty():
            raise SubjectDetectorUnavailable("Failed to load Haar cascade for face detection")

        self.cv2 = cv2
        self.np = np
        self.classifier = classifier

    def detect(self, image: Image.Image) -> List[Tuple[int, int, int, int]]:
        if image.mode != "RGB":
            image = image.convert("RGB")
        arr = self.np.array(image)
        gray = self.cv2.cvtColor(arr, self.cv2.COLOR_RGB2GRAY)
        boxes = self.classifier.detectMultiScale(
            gray,
            scaleFactor=1.05,
            minNeighbors=5,
            minSize=(32, 32),
        )
        if boxes is None:
            return []
        return [tuple(map(int, box)) for box in boxes]


class GenerativeFillProvider(Protocol):
    """Abstraction for plugging in a generative fill expansion service."""

    def expand(
        self,
        image: Image.Image,
        width: int,
        height: int,
        margin_x: int,
        margin_y: int,
    ) -> Image.Image:
        ...

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
    NO_CODE_MAN_RECIPE_ID = DEFAULT_NO_CODE_MAN_RECIPE_ID
    SOCIAL_THUMBNAIL_PRESETS = _SOCIAL_THUMBNAIL_PRESETS

    def __init__(
        self,
        media_service: Optional[MediaService] = None,
        subject_detector: Optional[SubjectDetector] = None,
        typography_service: Optional[TypographyService] = None,
        generative_fill_provider: Optional[GenerativeFillProvider] = None,
    ):
        self.media_service = media_service or get_media_service()
        self.backend = ImageCoreBackend(self.media_service)
        self._mask_cache: Dict[Tuple[str, str, str], DerivedArtifact] = {}
        self._subject_detector = subject_detector
        self._subject_mask_cache: Dict[Tuple[str, str, str, int, int], DerivedArtifact] = {}
        self._generative_fill_provider = generative_fill_provider
        self.typography_service = typography_service or TypographyService(
            media_service=self.media_service
        )

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

    def get_social_thumbnail_preset(self, preset_id: str) -> Optional[Dict[str, Any]]:
        config = self.SOCIAL_THUMBNAIL_PRESETS.get(preset_id)
        if not config:
            return None
        return deepcopy(config)

    def list_social_thumbnail_presets(self) -> List[Dict[str, Any]]:
        return [deepcopy(config) for config in self.SOCIAL_THUMBNAIL_PRESETS.values()]

    def detect_subject_mask(
        self,
        asset_id: str,
        width: int,
        height: int,
        tenant_id: str,
        env: str,
    ) -> str:
        if not asset_id:
            raise ValueError("asset_id is required for subject detection")
        if width <= 0 or height <= 0:
            raise ValueError("Mask width/height must be positive")
        if not tenant_id or not env:
            raise ValueError("tenant_id and env are required to create a subject mask")

        cache_key = (tenant_id, env, asset_id, width, height)
        cached = self._subject_mask_cache.get(cache_key)
        if cached:
            return cached.id

        asset = self.media_service.get_asset(asset_id)
        if not asset or not asset.source_uri:
            raise ValueError("Asset not found for subject detection")

        detector = self._ensure_subject_detector()
        with Image.open(asset.source_uri) as img:
            boxes = detector.detect(img)
            source_size = img.size

        if not boxes:
            raise SubjectDetectionFailure("Subject detector did not return any subjects")

        mask_img = self._render_subject_mask(boxes, width, height, source_size)
        signature = "|".join(f"{x},{y},{w},{h}" for x, y, w, h in boxes)
        cache_identifier = hashlib.sha256(f"{asset_id}:{width}:{height}:{signature}".encode()).hexdigest()

        out_io = io.BytesIO()
        mask_img.save(out_io, format="PNG")
        content = out_io.getvalue()
        filename = f"subject_mask_{asset_id[:6]}_{width}x{height}.png"

        up_req = MediaUploadRequest(
            tenant_id=tenant_id,
            env=env,
            kind="image",
            source_uri="pending",
            tags=["generated", "image_core", "subject_mask"],
            meta={"asset_id": asset_id, "width": width, "height": height},
        )

        new_asset = self.media_service.register_upload(up_req, filename, content)
        artifact = self.media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id=tenant_id,
                env=env,
                parent_asset_id=new_asset.id,
                kind="mask",
                uri=new_asset.source_uri,
                meta={
                    "backend_version": "image_subject_detector_v1",
                    "model_used": "opencv_haar_v1",
                    "cache_key": cache_identifier,
                    "detections": len(boxes),
                    "detection_boxes": [[x, y, w, h] for x, y, w, h in boxes],
                    "width": width,
                    "height": height,
                    "asset_id": asset_id,
                },
            )
        )

        self._subject_mask_cache[cache_key] = artifact
        return artifact.id

    def _ensure_subject_detector(self) -> SubjectDetector:
        if self._subject_detector is None:
            self._subject_detector = SubjectDetector()
        return self._subject_detector

    def _render_subject_mask(
        self,
        boxes: List[Tuple[int, int, int, int]],
        target_width: int,
        target_height: int,
        source_size: Tuple[int, int],
    ) -> Image.Image:
        mask = Image.new("L", (target_width, target_height), 0)
        draw = ImageDraw.Draw(mask)
        src_width, src_height = source_size
        if src_width <= 0 or src_height <= 0:
            raise ValueError("Source size must be positive for mask rendering")

        scale_x = target_width / src_width
        scale_y = target_height / src_height

        for x, y, w, h in boxes:
            left = max(0, min(int(x * scale_x), target_width))
            top = max(0, min(int(y * scale_y), target_height))
            right = max(left, min(int((x + w) * scale_x), target_width))
            bottom = max(top, min(int((y + h) * scale_y), target_height))
            draw.ellipse((left, top, right, bottom), fill=255)

        blur_radius = max(1, int(min(target_width, target_height) * 0.04))
        return mask.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    def create_social_thumbnail(
        self,
        asset_id: str,
        title: str,
        preset_id: str,
        tenant_id: str,
        env: str,
        extend_canvas: bool = False,
        bw_background: bool = True,
        extend_canvas_mode: Literal["mirror_blur", "generative_fill"] = "mirror_blur",
    ) -> DerivedArtifact:
        if not asset_id:
            raise ValueError("asset_id is required to build a thumbnail")
        if not title or not title.strip():
            raise ValueError("title is required for social thumbnail compositions")
        preset = self.get_social_thumbnail_preset(preset_id)
        if not preset:
            raise ValueError(f"Preset {preset_id} is not defined for COMFORT thumbnails")

        asset = self.media_service.get_asset(asset_id)
        if not asset:
            raise ValueError(f"Asset {asset_id} not found for thumbnail creation")
        subject_mask_id = self.detect_subject_mask(
            asset_id,
            preset["width"],
            preset["height"],
            tenant_id,
            env,
        )
        _, text_asset_id, text_meta = self.typography_service.render_text_with_metadata(
            self._build_headline_text_request(title, preset),
            tenant_id=tenant_id,
            env=env,
        )

        composition = self._plan_social_thumbnail_composition(
            asset_id,
            preset,
            subject_mask_id,
            text_asset_id,
            text_meta,
            bw_background,
            tenant_id,
            env,
        )

        pipeline_hash = self.backend.compute_pipeline_hash(composition)
        png_bytes = self.backend.render(composition, pipeline_hash=pipeline_hash)
        final_width = preset["width"]
        final_height = preset["height"]
        if extend_canvas:
            png_bytes, final_width, final_height = self.extend_canvas_mirror_blur(
                png_bytes,
                final_width,
                final_height,
                mode=extend_canvas_mode,
            )

        blend_modes = sorted({layer.blend_mode for layer in composition.layers})
        safe_box = _compute_safe_title_box(final_width, final_height)

        filename = f"social_thumb_{preset_id}_{uuid.uuid4().hex[:8]}.png"
        up_req = MediaUploadRequest(
            tenant_id=tenant_id,
            env=env,
            kind="image",
            source_uri="pending",
            tags=["generated", "image_core", "social_thumbnail", preset_id, preset["recipe_id"]],
            meta={"asset_id": asset_id},
        )
        new_asset = self.media_service.register_upload(up_req, filename, png_bytes)

        meta = {
            "width": final_width,
            "height": final_height,
            "pipeline_hash": pipeline_hash,
            "blend_modes": blend_modes,
            "preset_id": preset_id,
            "recipe_id": preset["recipe_id"],
            "subject_mask_id": subject_mask_id,
            "text_layout_hash": text_meta.layout_hash,
            "safe_title_box": safe_box,
        }

        artifact = self.media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id=tenant_id,
                env=env,
                parent_asset_id=new_asset.id,
                kind="image_render",
                uri=new_asset.source_uri,
                meta=meta,
            )
        )
        return artifact

    def _build_headline_text_request(
        self, title: str, preset: Dict[str, Any]
    ) -> TextLayoutRequest:
        safe_box = preset["safe_title_box"]
        font_size = max(32, int(safe_box["height"] * 0.45))
        return TextLayoutRequest(
            text=title,
            font_size_px=font_size,
            width=safe_box["width"],
            height=safe_box["height"],
            color_hex="#FFFFFF",
            color_overlay_hex="#FFFFFF",
            color_overlay_opacity=0.9,
            outer_glow_color_hex="#FFFFFF",
            outer_glow_opacity=0.75,
            outer_glow_radius_ratio=0.03,
        )

    def _plan_social_thumbnail_composition(
        self,
        asset_id: str,
        preset: Dict[str, Any],
        subject_mask_id: str,
        text_asset_id: str,
        text_meta: TextLayoutMetadata,
        bw_background: bool,
        tenant_id: str,
        env: str,
    ) -> ImageComposition:
        width = preset["width"]
        height = preset["height"]
        safe_box = preset["safe_title_box"]
        comp = ImageComposition(
            tenant_id=tenant_id,
            env=env,
            width=width,
            height=height,
            background_color="#000000",
        )
        comp.layers.append(
            ImageLayer(
                asset_id=asset_id,
                width=width,
                height=height,
                adjustments=self._background_adjustments(bw_background),
                filter_mode="blur",
                filter_strength=4.0,
            )
        )
        comp.layers.append(
            ImageLayer(
                asset_id=asset_id,
                width=width,
                height=height,
                mask_artifact_id=subject_mask_id,
                adjustments=self._foreground_adjustments(),
            )
        )
        text_x = safe_box["x"] + max(0, (safe_box["width"] - text_meta.width) // 2)
        text_y = safe_box["y"] + max(0, (safe_box["height"] - text_meta.height) // 2)
        comp.layers.append(
            ImageLayer(
                asset_id=text_asset_id,
                width=text_meta.width,
                height=text_meta.height,
                x=text_x,
                y=text_y,
            )
        )
        return comp

    def _background_adjustments(self, bw_background: bool) -> ImageAdjustment:
        adjustments = ImageAdjustment()
        adjustments.brightness = 0.78
        adjustments.contrast = 1.1
        adjustments.saturation = 0.0 if bw_background else 0.4
        adjustments.sharpness = 0.9
        return adjustments

    def _foreground_adjustments(self) -> ImageAdjustment:
        adjustments = ImageAdjustment()
        adjustments.brightness = 1.1
        adjustments.contrast = 1.25
        adjustments.saturation = 1.2
        adjustments.sharpness = 1.1
        return adjustments

    def extend_canvas_mirror_blur(
        self,
        png_bytes: bytes,
        width: int,
        height: int,
        margin_pct: float = 0.08,
        mode: Literal["mirror_blur", "generative_fill"] = "mirror_blur",
    ) -> Tuple[bytes, int, int]:
        margin_x = min(max(10, int(width * margin_pct)), max(1, width // 2))
        margin_y = min(max(10, int(height * margin_pct)), max(1, height // 2))
        new_width = width + margin_x * 2
        new_height = height + margin_y * 2
        src = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        # Future hook: swap mirror/blur edges for a generative-fill expansion when a provider is configured.
        if (
            mode == "generative_fill"
            and self._generative_fill_provider
            and margin_x > 0
            and margin_y > 0
        ):
            expanded = self._generative_fill_provider.expand(
                src, width, height, margin_x, margin_y
            )
            out_io = io.BytesIO()
            expanded.save(out_io, format="PNG")
            return out_io.getvalue(), expanded.width, expanded.height
        extended = Image.new("RGBA", (new_width, new_height), (0, 0, 0, 0))
        extended.paste(src, (margin_x, margin_y))
        if margin_x > 0:
            left_slice = src.crop((0, 0, margin_x, height))
            extended.paste(
                ImageOps.mirror(left_slice.resize((margin_x, height))), (0, margin_y)
            )
            right_slice = src.crop((width - margin_x, 0, width, height))
            extended.paste(
                ImageOps.mirror(right_slice.resize((margin_x, height))),
                (new_width - margin_x, margin_y),
            )
        if margin_y > 0:
            top_slice = src.crop((0, 0, width, margin_y))
            extended.paste(
                ImageOps.flip(top_slice.resize((width, margin_y))), (margin_x, 0)
            )
            bottom_slice = src.crop((0, height - margin_y, width, height))
            extended.paste(
                ImageOps.flip(bottom_slice.resize((width, margin_y))),
                (margin_x, new_height - margin_y),
            )
        if margin_x > 0 and margin_y > 0:
            corner = src.crop((0, 0, margin_x, margin_y))
            extended.paste(
                ImageOps.flip(ImageOps.mirror(corner)), (0, 0)
            )
            corner = src.crop((width - margin_x, 0, width, margin_y))
            extended.paste(
                ImageOps.flip(ImageOps.mirror(corner)), (new_width - margin_x, 0)
            )
            corner = src.crop((0, height - margin_y, margin_x, height))
            extended.paste(
                ImageOps.flip(ImageOps.mirror(corner)), (0, new_height - margin_y)
            )
            corner = src.crop((width - margin_x, height - margin_y, width, height))
            extended.paste(
                ImageOps.flip(ImageOps.mirror(corner)),
                (new_width - margin_x, new_height - margin_y),
            )
        blur_radius = max(1, int((margin_x + margin_y) * 0.4))
        blurred = extended.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        blurred.paste(src, (margin_x, margin_y), src)
        out_io = io.BytesIO()
        blurred.save(out_io, format="PNG")
        # Future hook: swap mirror/blur with generative fill when available.
        return out_io.getvalue(), new_width, new_height

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
