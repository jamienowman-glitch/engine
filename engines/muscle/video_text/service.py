from __future__ import annotations

import tempfile
from typing import Dict, Optional

from engines.media_v2.models import MediaUploadRequest
from engines.media_v2.service import MediaService, get_media_service
from engines.typography_core.models import TextLayoutRequest
from engines.typography_core.renderer import TextLayoutResult, TypographyRenderer
from engines.video_text.models import TextRenderRequest, TextRenderResponse


class VideoTextService:
    def __init__(self, media_service: Optional[MediaService] = None, renderer: Optional[TypographyRenderer] = None):
        self.media_service = media_service or get_media_service()
        self.renderer = renderer or TypographyRenderer()

    def render_text_image(self, req: TextRenderRequest) -> TextRenderResponse:
        if not req.text:
            raise ValueError("Text cannot be empty")

        layout_req = TextLayoutRequest(
            text=req.text,
            font_family=req.font_family,
            font_preset=req.font_preset,
            font_size_px=req.font_size_px,
            color_hex=req.color_hex,
            width=req.width,
            height=req.height,
            tracking=req.tracking,
            variation_settings=req.variation_settings,
        )

        layout: TextLayoutResult = self.renderer.render(layout_req)
        layout_meta = layout.metadata

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            layout.image.save(tmp.name, format="PNG")
            tmp_path = tmp.name

        upload_req = MediaUploadRequest(
            tenant_id=req.tenant_id,
            env=req.env,
            user_id=req.user_id,
            kind="image",
            source_uri=tmp_path,
            tags=["text_render", f"font_{layout_meta.font_id}"],
        )

        asset = self.media_service.register_remote(upload_req)

        return TextRenderResponse(
            asset_id=asset.id,
            uri=asset.source_uri or tmp_path,
            width=layout_meta.width,
            height=layout_meta.height,
            meta={
                "text_preview": req.text[:20],
                "font_family": layout_meta.font_family,
                "font_id": layout_meta.font_id,
                "font_preset": layout_meta.font_preset,
                "variant_axes": layout_meta.variation_axes,
                "tracking": layout_meta.tracking,
                "layout_hash": layout_meta.layout_hash,
            },
        )


_default_service: Optional[VideoTextService] = None


def get_video_text_service() -> VideoTextService:
    global _default_service
    if _default_service is None:
        _default_service = VideoTextService()
    return _default_service
