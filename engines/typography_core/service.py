from __future__ import annotations
import uuid
import io
from typing import Optional
from engines.media_v2.service import MediaService, get_media_service
from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest
from engines.typography_core.models import TextLayoutRequest
from engines.typography_core.renderer import TypographyRenderer

class TypographyService:
    def __init__(self, media_service: Optional[MediaService] = None):
        self.media_service = media_service or get_media_service()
        self.renderer = TypographyRenderer()

    def render_text_artifact(self, req: TextLayoutRequest, tenant_id: str, env: str) -> str:
        """
        Renders text and returns artifact ID (image_render type).
        """
        layout = self.renderer.render(req)
        img = layout.image
        layout_meta = layout.metadata

        out_io = io.BytesIO()
        img.save(out_io, format="PNG")
        content = out_io.getvalue()
        
        filename = f"text_{uuid.uuid4().hex[:8]}.png"
        
        up_req = MediaUploadRequest(
            tenant_id=tenant_id,
            env=env,
            kind="image",
            source_uri="pending",
            tags=["generated", "typography", "text"]
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
        return art.id

_default_service: Optional[TypographyService] = None

def get_typography_service() -> TypographyService:
    global _default_service
    if _default_service is None:
        _default_service = TypographyService()
    return _default_service
