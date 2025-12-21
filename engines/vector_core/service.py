from __future__ import annotations
import uuid
import io
from typing import Optional
from engines.media_v2.service import MediaService, get_media_service
from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest
from engines.vector_core.models import VectorScene
from engines.vector_core.renderer import VectorRenderer
from engines.vector_core.svg_parser import SVGParser

class VectorService:
    def __init__(self, media_service: Optional[MediaService] = None):
        self.media_service = media_service or get_media_service()
        self.renderer = VectorRenderer()
        self.parser = SVGParser()

    def rasterize_scene_artifact(self, scene: VectorScene) -> str:
        layout_hash = scene.compute_layout_hash()
        scene.meta["layout_hash"] = layout_hash

        img = self.renderer.render(scene)
        
        out_io = io.BytesIO()
        img.save(out_io, format="PNG")
        content = out_io.getvalue()
        
        filename = f"vector_{uuid.uuid4().hex[:8]}.png"
        
        up_req = MediaUploadRequest(
            tenant_id=scene.tenant_id,
            env=scene.env,
            kind="image",
            source_uri="pending",
            tags=["generated", "vector_core"]
        )
        new_asset = self.media_service.register_upload(up_req, filename, content)
        
        art = self.media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id=scene.tenant_id,
                env=scene.env,
                parent_asset_id=new_asset.id,
                kind="image_render",
                uri=new_asset.source_uri,
                meta={
                    "width": img.width,
                    "height": img.height,
                    "layout_hash": layout_hash,
                    "boolean_ops": scene.meta.get("boolean_ops", "none"),
                }
            )
        )
        return art.id

_default_service: Optional[VectorService] = None

def get_vector_service() -> VectorService:
    global _default_service
    if _default_service is None:
        _default_service = VectorService()
    return _default_service
