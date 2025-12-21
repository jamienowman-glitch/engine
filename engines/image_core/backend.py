import io
import json
import hashlib
from typing import Optional, Tuple, Dict, Any, List
from PIL import Image, ImageEnhance, ImageChops, ImageColor, ImageFilter, ImageOps
from engines.image_core.models import ImageComposition, ImageLayer, BlendMode, FilterMode
from pydantic import BaseModel
from engines.media_v2.service import MediaService
from engines.typography_core.renderer import TypographyRenderer
from engines.typography_core.models import TextLayoutRequest

from engines.vector_core.renderer import VectorRenderer

class ImageCoreBackend:
    def __init__(self, media_service: MediaService):
        self.media_service = media_service
        self.text_renderer = TypographyRenderer()
        self.vector_renderer = VectorRenderer()
        self._cache: Dict[str, bytes] = {}

    def compute_pipeline_hash(self, comp: ImageComposition) -> str:
        payload = self._composition_payload(comp)
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def _composition_payload(self, comp: ImageComposition) -> Dict[str, Any]:
        payload = comp.model_dump()
        payload.pop("id", None)
        layers = []
        for layer in comp.layers:
            layer_dict = layer.model_dump()
            layer_dict.pop("id", None)
            layers.append(self._normalize_value(layer_dict))
        payload["layers"] = layers
        return self._normalize_value(payload)

    def _normalize_value(self, value: Any) -> Any:
        if isinstance(value, BaseModel):
            return self._normalize_value(value.model_dump())
        if isinstance(value, dict):
            return {k: self._normalize_value(value[k]) for k in sorted(value)}
        if isinstance(value, list):
            return [self._normalize_value(v) for v in value]
        if isinstance(value, tuple):
            return [self._normalize_value(v) for v in value]
        return value

    def _apply_adjustments(self, img: Image.Image, layer: ImageLayer) -> Image.Image:
        adj = layer.adjustments
        if adj.exposure != 0.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(2 ** adj.exposure)
        if adj.brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(adj.brightness)
        if adj.contrast != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(adj.contrast)
        if adj.saturation != 1.0:
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(adj.saturation)
        if adj.sharpness != 1.0:
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(adj.sharpness)
        if adj.gamma != 1.0:
            try:
                img = ImageOps.gamma(img, adj.gamma)
            except Exception:
                pass
        return img

    def _apply_blend_mode(self, base: Image.Image, top: Image.Image, mode: BlendMode) -> Image.Image:
        # Both images must be RGBA
        if mode == "normal":
            # Pillow's paste/alpha_composite handles normal with opacity
            return base # handled by alpha_composite outside
        
        # For blend modes, we use ImageChops
        # ImageChops expects same size images usually
        # Crop/resize top to match base or vice versa is usually required for Chops
        # But here 'top' is a layer placed on 'base' canvas.
        # So we should crop the relevant part of base, blend, and paste back?
        # Or faster: Composite full size transparent layer?
        # Creating full size layer for blend is safer for correctness.
        
        # Ensure proper mode
        top = top.convert("RGBA")
        base = base.convert("RGBA")
        
        # NOTE: PIL Chops often don't respect alpha correctly for "overlay" etc in standard Photoshop way
        # But let's try standard mapping
        
        blended = top
        if mode == "multiply":
            blended = ImageChops.multiply(base, top)
        elif mode == "screen":
            blended = ImageChops.screen(base, top)
        elif mode == "darken":
            blended = ImageChops.darker(base, top)
        elif mode == "lighten":
            blended = ImageChops.lighter(base, top)
        elif mode == "add":
            blended = ImageChops.add(base, top)
        elif mode == "overlay":
            # Overlay is hard in vanilla PIL without numpy
            # Fallback to overlay simulation or soft light
            blended = ImageChops.overlay(base, top)
            
        return blended

    def _load_layer_content(self, layer: ImageLayer) -> Optional[Image.Image]:
        if layer.asset_id:
            asset = self.media_service.get_asset(layer.asset_id)
            if asset and asset.source_uri:
                try:
                    return Image.open(asset.source_uri).convert("RGBA")
                except Exception:
                    return None
        if layer.color:
            color = ImageColor.getcolor(layer.color, "RGBA")
            width = layer.width or 100
            height = layer.height or 100
            return Image.new("RGBA", (width, height), color)
        if layer.text:
            req = TextLayoutRequest(
                text=layer.text,
                font_family=layer.text_font,
                font_preset=layer.text_preset,
                font_size_px=layer.text_size,
                color_hex=layer.text_color,
                width=layer.width if layer.width else None,
                tracking=layer.text_tracking,
                variation_settings=layer.text_variation_settings,
            )
            return self.text_renderer.render(req).image.convert("RGBA")
        if layer.vector_scene:
            return self.vector_renderer.render(layer.vector_scene, width=layer.width, height=layer.height).convert("RGBA")
        return None

    def _adjust_layer_geometry(self, img: Image.Image, layer: ImageLayer) -> Image.Image:
        target_w = layer.width or img.width
        target_h = layer.height or img.height
        if layer.scale != 1.0:
            target_w = max(1, int(target_w * layer.scale))
            target_h = max(1, int(target_h * layer.scale))
        if target_w != img.width or target_h != img.height:
            img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        if layer.rotation != 0.0:
            img = img.rotate(-layer.rotation, resample=Image.Resampling.BICUBIC, expand=True)
        return img

    def _apply_adjustments_and_filters(self, img: Image.Image, layer: ImageLayer) -> Image.Image:
        img = self._apply_adjustments(img, layer)
        if layer.filter_mode != "none":
            img = self._apply_filter(img, layer)
        return img

    def _apply_adjustments(self, img: Image.Image, layer: ImageLayer) -> Image.Image:
        adj = layer.adjustments
        if adj.exposure != 0.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(2 ** adj.exposure)
        if adj.brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(adj.brightness)
        if adj.contrast != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(adj.contrast)
        if adj.saturation != 1.0:
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(adj.saturation)
        if adj.sharpness != 1.0:
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(adj.sharpness)
        if adj.gamma != 1.0:
            try:
                img = ImageOps.gamma(img, adj.gamma)
            except Exception:
                pass
        return img

    def _apply_filter(self, img: Image.Image, layer: ImageLayer) -> Image.Image:
        strength = max(0.1, layer.filter_strength)
        if layer.filter_mode == "blur":
            return img.filter(ImageFilter.GaussianBlur(radius=strength))
        if layer.filter_mode == "sharpen":
            percent = min(300, int(150 * strength))
            return img.filter(ImageFilter.UnsharpMask(radius=1, percent=percent, threshold=3))
        return img

    def _load_mask(self, layer: ImageLayer, width: int, height: int) -> Optional[Image.Image]:
        mask_img = None
        if layer.mask:
            from engines.image_core.selections import rasterize_selection
            mask_img = rasterize_selection(layer.mask, width, height)
        elif layer.mask_artifact_id:
            mask_img = self._load_mask_artifact(layer.mask_artifact_id, width, height)
        return mask_img

    def _load_mask_artifact(self, artifact_id: str, width: int, height: int) -> Optional[Image.Image]:
        art = self.media_service.get_artifact(artifact_id)
        if not art or not art.uri:
            return None
        try:
            mask_img = Image.open(art.uri).convert("L")
            if mask_img.size != (width, height):
                mask_img = mask_img.resize((width, height), Image.Resampling.BILINEAR)
            return mask_img
        except Exception:
            return None

    def render(self, comp: ImageComposition, pipeline_hash: Optional[str] = None) -> bytes:
        if pipeline_hash is None:
            pipeline_hash = self.compute_pipeline_hash(comp)
        cached = self._cache.get(pipeline_hash)
        if cached is not None:
            return cached
        payload = self._render_internal(comp)
        self._cache[pipeline_hash] = payload
        return payload

    def _render_internal(self, comp: ImageComposition) -> bytes:
        bg_color = ImageColor.getcolor(comp.background_color, "RGBA")
        canvas = Image.new("RGBA", (comp.width, comp.height), bg_color)
        for layer in comp.layers:
            src_img = self._load_layer_content(layer)
            if not src_img:
                continue

            src_img = self._adjust_layer_geometry(src_img, layer)
            src_img = self._apply_adjustments_and_filters(src_img, layer)
            opacity = max(0.0, min(layer.opacity, 1.0))
            if opacity < 1.0:
                r, g, b, a = src_img.split()
                a = a.point(lambda p: int(p * opacity))
                src_img = Image.merge("RGBA", (r, g, b, a))

            layer_canvas = Image.new("RGBA", (comp.width, comp.height), (0, 0, 0, 0))
            layer_canvas.paste(src_img, (layer.x, layer.y), src_img)

            mask_img = self._load_mask(layer, comp.width, comp.height)
            if mask_img:
                r, g, b, a = layer_canvas.split()
                a = ImageChops.multiply(a, mask_img)
                layer_canvas = Image.merge("RGBA", (r, g, b, a))

            if layer.blend_mode == "normal":
                canvas = Image.alpha_composite(canvas, layer_canvas)
            else:
                blended = self._apply_blend_mode(canvas, layer_canvas, layer.blend_mode)
                canvas = Image.alpha_composite(canvas, blended)

        out_io = io.BytesIO()
        canvas.save(out_io, format="PNG")
        return out_io.getvalue()
