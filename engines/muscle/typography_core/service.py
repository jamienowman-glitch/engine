from __future__ import annotations
import uuid
import io
from typing import Optional, Tuple
from PIL import Image, ImageColor, ImageFilter
from engines.media_v2.service import MediaService, get_media_service
from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest
from engines.typography_core.models import TextLayoutRequest
from engines.typography_core.renderer import TypographyRenderer, TextLayoutMetadata

class TypographyService:
    def __init__(self, media_service: Optional[MediaService] = None):
        self.media_service = media_service or get_media_service()
        self.renderer = TypographyRenderer()

    def render_text_artifact(self, req: TextLayoutRequest, tenant_id: str, env: str) -> str:
        """
        Renders text and returns artifact ID (image_render type).
        """
        artifact_id, _, _ = self._render_text_artifact_internal(req, tenant_id, env)
        return artifact_id

    def render_text_with_metadata(
        self, req: TextLayoutRequest, tenant_id: str, env: str
    ) -> Tuple[str, str, TextLayoutMetadata]:
        """
        Renders text and returns artifact/asset IDs plus layout metadata.
        """
        return self._render_text_artifact_internal(req, tenant_id, env)

    def _render_text_artifact_internal(
        self, req: TextLayoutRequest, tenant_id: str, env: str
    ) -> Tuple[str, str, TextLayoutMetadata]:
        layout = self.renderer.render(req)
        img = layout.image.convert("RGBA")
        layout_meta = layout.metadata

        base_mask = layout.image.split()[3]
        img = self._apply_outer_glow(img, base_mask, req)
        img = self._apply_text_overlay(img, base_mask, req)

        out_io = io.BytesIO()
        img.save(out_io, format="PNG")
        content = out_io.getvalue()

        filename = f"text_{uuid.uuid4().hex[:8]}.png"

        up_req = MediaUploadRequest(
            tenant_id=tenant_id,
            env=env,
            kind="image",
            source_uri="pending",
            tags=["generated", "typography", "text"],
        )

        new_asset = self.media_service.register_upload(up_req, filename, content)

        art = self.media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id=tenant_id,
                env=env,
                parent_asset_id=new_asset.id,
                kind="image_render",  # Treat as image render
                uri=new_asset.source_uri,
                meta={
                    "text_preview": req.text[:20],
                    "font_family": layout_meta.font_family,
                    "font_id": layout_meta.font_id,
                    "font_preset": layout_meta.font_preset,
                    "variant_axes": layout_meta.variation_axes,
                    "tracking": layout_meta.tracking,
                    "layout_hash": layout_meta.layout_hash,
                    "width": layout_meta.width,
                    "height": layout_meta.height,
                },
            )
        )
        return art.id, new_asset.id, layout_meta

    def _apply_text_overlay(
        self, image: Image.Image, mask: Image.Image, req: TextLayoutRequest
    ) -> Image.Image:
        if not req.color_overlay_hex or req.color_overlay_opacity is None:
            return image
        opacity = max(0.0, min(req.color_overlay_opacity, 1.0))
        overlay_color = ImageColor.getcolor(req.color_overlay_hex, "RGBA")
        overlay_mask = mask.point(lambda p: int(p * opacity))
        overlay_layer = Image.new("RGBA", image.size, overlay_color[:3] + (0,))
        overlay_layer.putalpha(overlay_mask)
        return Image.alpha_composite(image, overlay_layer)

    def _apply_outer_glow(
        self, image: Image.Image, mask: Image.Image, req: TextLayoutRequest
    ) -> Image.Image:
        if (
            not req.outer_glow_color_hex
            or req.outer_glow_opacity is None
            or req.outer_glow_radius_ratio is None
        ):
            return image
        opacity = max(0.0, min(req.outer_glow_opacity, 1.0))
        radius = max(1, int(min(image.size) * req.outer_glow_radius_ratio))
        glow_mask = mask.filter(ImageFilter.GaussianBlur(radius=radius))
        glow_mask = glow_mask.point(lambda p: int(p * opacity))
        glow_color = ImageColor.getcolor(req.outer_glow_color_hex, "RGBA")
        glow_layer = Image.new("RGBA", image.size, glow_color[:3] + (0,))
        glow_layer.putalpha(glow_mask)
        return Image.alpha_composite(glow_layer, image)

_default_service: Optional[TypographyService] = None

def get_typography_service() -> TypographyService:
    global _default_service
    if _default_service is None:
        _default_service = TypographyService()
    return _default_service
