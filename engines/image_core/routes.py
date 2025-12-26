"""HTTP routes for image_core service."""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field

from engines.image_core.models import ImageComposition, ImageLayer
from engines.image_core.service import ImageCoreService, get_image_core_service
from engines.image_core.template_service import get_template_service
from engines.image_core.template_models import CompositionTemplate, RenderFromTemplateRequest
from engines.image_core.api_models import (
    RenderCompositionRequest,
    BatchRenderRequest,
    RenderResponse,
    BatchRenderResponse,
    PresetInfo,
    PresetsListResponse,
)

router = APIRouter(prefix="/image", tags=["image_core"])


class SocialThumbnailPreset(BaseModel):
    preset_id: str
    width: int
    height: int
    aspect_ratio: str
    format: str
    quality: Optional[int]
    recipe_id: str
    safe_title_box: Dict[str, Any]


class SocialThumbnailListResponse(BaseModel):
    presets: List[SocialThumbnailPreset]
    total_count: int


class SocialThumbnailRecipeRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant ID")
    env: str = Field(..., description="Environment (dev/test/prod)")
    asset_id: str = Field(..., description="Source asset ID for the photo")
    preset_id: str = Field(..., description="Social thumbnail preset (e.g., 'youtube_thumb_16_9')")
    title: str = Field(..., description="Headline text for the thumbnail")
    extend_canvas: bool = Field(default=False, description="Extend the canvas with mirror/blur edges")
    bw_background: bool = Field(default=True, description="Render the background in black & white")
    canvas_extension_mode: Literal["mirror_blur", "generative_fill"] = Field(
        default="mirror_blur",
        description="Extension strategy—fallback to mirror/blur unless a generative fill provider is configured",
    )


class SocialThumbnailRecipeResponse(BaseModel):
    artifact_id: str
    preset_id: str
    recipe_id: str
    subject_mask_id: Optional[str]
    width: int
    height: int
    safe_title_box: Dict[str, Any]
    meta: Dict[str, Any]


def _composition_from_dict(data: Dict[str, Any]) -> ImageComposition:
    """Convert dict to ImageComposition model."""
    try:
        layers_data = data.get("layers", [])
        layers = []
        for layer_dict in layers_data:
            layer = ImageLayer(**layer_dict)
            layers.append(layer)
        
        comp = ImageComposition(
            tenant_id=data.get("tenant_id", ""),
            env=data.get("env", ""),
            width=data.get("width", 1920),
            height=data.get("height", 1080),
            background_color=data.get("background_color", "#FFFFFF"),
            layers=layers,
        )
        return comp
    except Exception as e:
        raise ValueError(f"Invalid composition data: {e}")


@router.post("/render", response_model=RenderResponse)
def render_composition(req: RenderCompositionRequest) -> RenderResponse:
    """
    Render a composition with optional preset.
    
    Args:
        req: RenderCompositionRequest with composition and optional preset
        
    Returns:
        RenderResponse with artifact_id and metadata
    """
    try:
        # Inject tenant/env into composition data
        comp_data = req.composition.copy()
        comp_data["tenant_id"] = req.tenant_id
        comp_data["env"] = req.env
        
        comp = _composition_from_dict(comp_data)
        
        service = get_image_core_service()
        artifact_id = service.render_composition(
            comp,
            parent_asset_id=req.parent_asset_id,
            preset_id=req.preset_id,
        )
        
        artifact = service.media_service.get_artifact(artifact_id)
        if not artifact:
            raise HTTPException(status_code=500, detail="Failed to retrieve artifact")
        
        meta = artifact.meta or {}
        return RenderResponse(
            artifact_id=artifact_id,
            format=meta.get("format", "PNG"),
            width=meta.get("width", comp.width),
            height=meta.get("height", comp.height),
            preset_id=req.preset_id,
            meta=meta,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Render failed: {e}")


@router.post("/batch-render", response_model=BatchRenderResponse)
def batch_render_composition(req: BatchRenderRequest) -> BatchRenderResponse:
    """
    Render a composition with multiple presets in one call (optimized).
    
    Uses single pipeline render + efficient preset transformations.
    
    Args:
        req: BatchRenderRequest with composition and list of preset_ids
        
    Returns:
        BatchRenderResponse with all results mapped by preset_id
    """
    try:
        comp_data = req.composition.copy()
        comp_data["tenant_id"] = req.tenant_id
        comp_data["env"] = req.env
        
        comp = _composition_from_dict(comp_data)
        service = get_image_core_service()
        
        # Use optimized batch_render
        results_map = service.batch_render(comp, req.preset_ids)
        
        results: Dict[str, RenderResponse] = {}
        for preset_id, artifact_id in results_map.items():
            artifact = service.media_service.get_artifact(artifact_id)
            if artifact:
                meta = artifact.meta or {}
                results[preset_id] = RenderResponse(
                    artifact_id=artifact_id,
                    format=meta.get("format", "PNG"),
                    width=meta.get("width", comp.width),
                    height=meta.get("height", comp.height),
                    preset_id=preset_id,
                    meta=meta,
                )
        
        if not results:
            raise HTTPException(status_code=500, detail="No presets rendered successfully")
        
        return BatchRenderResponse(
            results=results,
            total_count=len(results),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch render failed: {e}")


@router.post("/batch-render-optimized", response_model=BatchRenderResponse)
def batch_render_optimized(req: BatchRenderRequest) -> BatchRenderResponse:
    """Alias for /batch-render using optimized single-pass rendering."""
    return batch_render_composition(req)



@router.get("/presets", response_model=PresetsListResponse)
def list_presets() -> PresetsListResponse:
    """
    List all available export presets with details.
    
    Returns:
        PresetsListResponse with full preset information
    """
    service = get_image_core_service()
    presets_info: list[PresetInfo] = []
    
    # Categorize presets
    categories = {
        "web": ["web_small", "web_medium", "web_large", "original"],
        "social": ["instagram_1080", "instagram_story_1080x1920", "twitter_card_1200x675", 
                   "linkedin_banner_1584x396", "facebook_cover_820x312", "pinterest_pin_1000x1500",
                   "social_1080p"],
        "video": ["tiktok_video_1080x1920", "snapchat_story_1080x1920", "youtube_thumbnail_1280x720"],
        "email": ["email_header_600x200", "email_body_600x400", "newsletter_banner_640", "web_og_image_1200x630"],
        "ecommerce": ["ecommerce_product_400x400", "ecommerce_product_800x800", "ecommerce_gallery_1200x1200"],
        "icons": ["avatar_64x64", "avatar_128x128", "icon_256x256", "icon_512x512", "thumbnail_200"],
        "display": ["desktop_1920x1080", "desktop_2560x1440", "ultrawide_3440x1440", "retina_display_2x", 
                    "hero_1920x1080", "mobile_small_640x360"],
        "ads": ["google_ads_300x250", "google_ads_728x90", "facebook_ads_1200x628", "banner_970x250"],
        "print": ["print_a4_300dpi", "print_a3_300dpi", "print_postcard_4x6_300dpi", 
                  "print_business_card_3_5x2_300dpi", "print_poster_18x24_300dpi", "print_300dpi"],
        "draft": ["draft_preview_480", "draft_preview_720"],
        "archive": ["tiff_high_quality"],
    }
    
    for category, preset_ids in categories.items():
        for preset_id in preset_ids:
            preset_config = service.PRESETS.get(preset_id)
            if preset_config:
                presets_info.append(
                    PresetInfo(
                        preset_id=preset_id,
                        format=preset_config.get("format", "PNG"),
                        width=preset_config.get("width"),
                        height=preset_config.get("height"),
                        quality=preset_config.get("quality"),
                        dpi=preset_config.get("dpi"),
                        category=category,
                    )
                )
    
    return PresetsListResponse(
        presets=presets_info,
        total_count=len(presets_info),
    )


@router.get("/social-thumbnails", response_model=SocialThumbnailListResponse)
def list_social_thumbnail_presets() -> SocialThumbnailListResponse:
    """
    List the COMFORT social thumbnail recipe presets with safe-title defaults.
    """
    service = get_image_core_service()
    presets = service.list_social_thumbnail_presets()
    return SocialThumbnailListResponse(
        presets=[SocialThumbnailPreset(**preset) for preset in presets],
        total_count=len(presets),
    )


@router.post("/social-thumbnails/recipe", response_model=SocialThumbnailRecipeResponse)
def create_social_thumbnail(req: SocialThumbnailRecipeRequest) -> SocialThumbnailRecipeResponse:
    """
    Build a COMFORT social thumbnail via the No-Code-Man recipe.
    """
    service = get_image_core_service()
    try:
        artifact = service.create_social_thumbnail(
            req.asset_id,
            req.title,
            req.preset_id,
            req.tenant_id,
            req.env,
            extend_canvas=req.extend_canvas,
            extend_canvas_mode=req.canvas_extension_mode,
            bw_background=req.bw_background,
        )
        meta = artifact.meta or {}
        preset = service.get_social_thumbnail_preset(req.preset_id)
        width = meta.get("width", preset["width"] if preset else 0)
        height = meta.get("height", preset["height"] if preset else 0)
        safe_box = meta.get(
            "safe_title_box", preset["safe_title_box"] if preset else {}
        )
        return SocialThumbnailRecipeResponse(
            artifact_id=artifact.id,
            preset_id=meta.get("preset_id", req.preset_id),
            recipe_id=meta.get("recipe_id", service.NO_CODE_MAN_RECIPE_ID),
            subject_mask_id=meta.get("subject_mask_id"),
            width=width,
            height=height,
            safe_title_box=safe_box,
            meta=meta,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to create social thumbnail: {exc}"
        )


# ============================================================================
# TEMPLATE ROUTES
# ============================================================================


@router.post("/templates", response_model=CompositionTemplate)
def save_template(template: CompositionTemplate) -> CompositionTemplate:
    """
    Save a reusable composition template.
    
    Args:
        template: CompositionTemplate with layers and variables
        
    Returns:
        Saved template
    """
    try:
        svc = get_template_service()
        return svc.save_template(template)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save template: {e}")


@router.get("/templates/{template_id}", response_model=CompositionTemplate)
def get_template(template_id: str) -> CompositionTemplate:
    """Get a template by ID."""
    svc = get_template_service()
    template = svc.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.get("/templates", response_model=Dict[str, Any])
def list_templates(tenant_id: str, category: Optional[str] = None) -> Dict[str, Any]:
    """
    List templates for a tenant.
    
    Args:
        tenant_id: Tenant ID
        category: Optional category filter (social, email, print, etc)
        
    Returns:
        Dict with templates list and total count
    """
    svc = get_template_service()
    templates = svc.list_templates(tenant_id, category)
    return {
        "templates": templates,
        "total_count": len(templates),
    }


@router.delete("/templates/{template_id}")
def delete_template(template_id: str) -> Dict[str, Any]:
    """Delete a template by ID."""
    svc = get_template_service()
    if svc.delete_template(template_id):
        return {"status": "deleted", "template_id": template_id}
    raise HTTPException(status_code=404, detail="Template not found")


@router.post("/render-from-template", response_model=RenderResponse)
def render_from_template(req: RenderFromTemplateRequest) -> RenderResponse:
    """
    Render a composition from a template with variable substitution.
    
    Args:
        req: RenderFromTemplateRequest with template_id and variable values
        
    Returns:
        RenderResponse with artifact_id and metadata
    """
    try:
        image_svc = get_image_core_service()
        template_svc = get_template_service()
        
        artifact_id = template_svc.render_from_template(
            template_id=req.template_id,
            tenant_id=req.tenant_id,
            env=req.env,
            variables=req.variables,
            image_service=image_svc,
            preset_id=req.preset_id,
            parent_asset_id=req.parent_asset_id,
        )
        
        artifact = image_svc.media_service.get_artifact(artifact_id)
        if not artifact:
            raise HTTPException(status_code=500, detail="Failed to retrieve artifact")
        
        meta = artifact.meta or {}
        return RenderResponse(
            artifact_id=artifact_id,
            format=meta.get("format", "PNG"),
            width=meta.get("width", 0),
            height=meta.get("height", 0),
            preset_id=req.preset_id,
            meta=meta,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Render from template failed: {e}")


@router.post("/calculate-crop")
def calculate_crop(
    source_width: int,
    source_height: int,
    aspect_ratio: str,
    focal_x: Optional[float] = None,
    focal_y: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Calculate optimal crop box for target aspect ratio.
    
    Args:
        source_width: Original image width in pixels
        source_height: Original image height in pixels
        aspect_ratio: Target ratio as "W:H" (e.g., "16:9", "1:1", "4:3")
        focal_x: Optional focal point X (0-1, normalized)
        focal_y: Optional focal point Y (0-1, normalized)
    
    Returns:
        Dict with crop_box coordinates, confidence, method used
    """
    try:
        if source_width <= 0 or source_height <= 0:
            raise ValueError("Width and height must be positive")
        
        svc = get_image_core_service()
        focal_point = None
        if focal_x is not None and focal_y is not None:
            focal_point = (focal_x, focal_y)
        
        return svc.calculate_auto_crop(
            source_width=source_width,
            source_height=source_height,
            aspect_ratio=aspect_ratio,
            focal_point=focal_point
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crop calculation failed: {e}")


@router.get("/presets/crop")
def get_crop_presets() -> Dict[str, str]:
    """
    List all available crop presets with their aspect ratios.
    Useful for UI/agent to discover available presets.
    """
    from engines.image_core.auto_crop import AutoCropEngine
    return AutoCropEngine.PRESET_RATIOS


@router.post("/crop-for-preset")
def crop_for_preset(
    preset_name: str,
    source_width: int,
    source_height: int,
    focal_x: Optional[float] = None,
    focal_y: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Get crop box for a named preset (e.g., "instagram-square").
    
    Args:
        preset_name: Preset identifier
        source_width: Original image width
        source_height: Original image height
        focal_x: Optional focal point X (0-1)
        focal_y: Optional focal point Y (0-1)
    
    Returns:
        Dict with crop_box or error if preset not found
    """
    try:
        if source_width <= 0 or source_height <= 0:
            raise ValueError("Width and height must be positive")
        
        svc = get_image_core_service()
        focal_point = None
        if focal_x is not None and focal_y is not None:
            focal_point = (focal_x, focal_y)
        
        result = svc.get_crop_for_preset(
            preset_name=preset_name,
            source_width=source_width,
            source_height=source_height,
            focal_point=focal_point
        )
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Preset '{preset_name}' not found")
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crop for preset failed: {e}")

# ============================================================================
# ASSET VERSIONING ROUTES
# ============================================================================

@router.post("/assets/{asset_id}/versions")
def create_asset_version(
    asset_id: str,
    artifact_id: str,
    file_hash: str,
    file_size: int,
    created_by: Optional[str] = None,
    description: str = "",
    tags: Optional[List[str]] = None,
    mime_type: str = "image/png",
) -> Dict[str, Any]:
    """
    Create a new version of an asset.
    
    Args:
        asset_id: Asset identifier
        artifact_id: Media artifact ID
        file_hash: SHA256 hash of file content
        file_size: File size in bytes
        created_by: Optional creator identifier
        description: Version description
        tags: Optional list of tags
        mime_type: MIME type of asset
    
    Returns:
        AssetVersion data
    """
    try:
        from engines.image_core.versioning import get_versioning_service
        
        svc = get_versioning_service()
        version = svc.create_version(
            asset_id=asset_id,
            artifact_id=artifact_id,
            file_hash=file_hash,
            file_size=file_size,
            created_by=created_by,
            description=description,
            tags=tags,
            mime_type=mime_type
        )
        
        return {
            "asset_id": version.asset_id,
            "version_number": version.version_number,
            "artifact_id": version.artifact_id,
            "status": version.status,
            "file_hash": version.file_hash,
            "file_size": version.file_size,
            "created_at": version.metadata.created_at.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create version: {e}")


@router.get("/assets/{asset_id}/versions")
def list_asset_versions(asset_id: str) -> Dict[str, Any]:
    """
    List all versions of an asset.
    
    Args:
        asset_id: Asset identifier
    
    Returns:
        List of asset versions with metadata
    """
    try:
        from engines.image_core.versioning import get_versioning_service
        
        svc = get_versioning_service()
        versions = svc.get_all_versions(asset_id)
        
        return {
            "asset_id": asset_id,
            "versions": [
                {
                    "version_number": v.version_number,
                    "artifact_id": v.artifact_id,
                    "status": v.status,
                    "file_hash": v.file_hash,
                    "file_size": v.file_size,
                    "created_at": v.metadata.created_at.isoformat(),
                    "description": v.metadata.description,
                    "tags": v.metadata.tags,
                }
                for v in versions
            ],
            "total_versions": len(versions),
            "latest_version": versions[-1].version_number if versions else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list versions: {e}")


@router.get("/assets/{asset_id}/versions/latest")
def get_latest_asset_version(asset_id: str) -> Dict[str, Any]:
    """
    Get the latest active version of an asset.
    
    Args:
        asset_id: Asset identifier
    
    Returns:
        Latest active AssetVersion
    """
    try:
        from engines.image_core.versioning import get_versioning_service
        
        svc = get_versioning_service()
        version = svc.get_latest_version(asset_id)
        
        if not version:
            raise HTTPException(status_code=404, detail=f"No active version found for asset '{asset_id}'")
        
        return {
            "asset_id": version.asset_id,
            "version_number": version.version_number,
            "artifact_id": version.artifact_id,
            "status": version.status,
            "file_hash": version.file_hash,
            "file_size": version.file_size,
            "created_at": version.metadata.created_at.isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get latest version: {e}")


@router.get("/assets/{asset_id}/versions/{version_number}")
def get_asset_version(asset_id: str, version_number: int) -> Dict[str, Any]:
    """
    Get a specific version of an asset.
    
    Args:
        asset_id: Asset identifier
        version_number: Version number
    
    Returns:
        AssetVersion data
    """
    try:
        from engines.image_core.versioning import get_versioning_service
        
        svc = get_versioning_service()
        version = svc.get_version(asset_id, version_number)
        
        if not version:
            raise HTTPException(status_code=404, detail=f"Version {version_number} not found for asset '{asset_id}'")
        
        return {
            "asset_id": version.asset_id,
            "version_number": version.version_number,
            "artifact_id": version.artifact_id,
            "status": version.status,
            "file_hash": version.file_hash,
            "file_size": version.file_size,
            "created_at": version.metadata.created_at.isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get version: {e}")


@router.post("/assets/{asset_id}/versions/{version_number}/deprecate")
def deprecate_asset_version(asset_id: str, version_number: int) -> Dict[str, Any]:
    """
    Mark an asset version as deprecated.
    
    Args:
        asset_id: Asset identifier
        version_number: Version number to deprecate
    
    Returns:
        Success status
    """
    try:
        from engines.image_core.versioning import get_versioning_service
        
        svc = get_versioning_service()
        success = svc.deprecate_version(asset_id, version_number)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Version {version_number} not found")
        
        return {"status": "deprecated", "asset_id": asset_id, "version_number": version_number}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to deprecate version: {e}")


@router.post("/renders/{render_id}/lineage")
def record_render_lineage(
    render_id: str,
    tenant_id: str,
    env: str,
    assets_used: List[Dict[str, Any]],
    composition_id: Optional[str] = None,
    composition_hash: str = "",
) -> Dict[str, Any]:
    """
    Record which asset versions were used in a render.
    
    Args:
        render_id: Render artifact ID
        tenant_id: Tenant identifier
        env: Environment
        assets_used: List of {asset_id, version_number, layer_id, file_hash}
        composition_id: Optional composition identifier
        composition_hash: Hash of composition at render time
    
    Returns:
        Recorded lineage
    """
    try:
        from engines.image_core.versioning import get_versioning_service, RenderLineageEntry
        
        svc = get_versioning_service()
        
        # Convert to RenderLineageEntry objects
        entries = [
            RenderLineageEntry(
                asset_id=entry["asset_id"],
                version_number=entry["version_number"],
                layer_id=entry["layer_id"],
                file_hash=entry["file_hash"]
            )
            for entry in assets_used
        ]
        
        lineage = svc.record_render_lineage(
            render_id=render_id,
            tenant_id=tenant_id,
            env=env,
            assets_used=entries,
            composition_id=composition_id,
            composition_hash=composition_hash
        )
        
        return {
            "render_id": lineage.render_id,
            "composition_id": lineage.composition_id,
            "assets_used": [
                {
                    "asset_id": entry.asset_id,
                    "version_number": entry.version_number,
                    "layer_id": entry.layer_id
                }
                for entry in lineage.assets_used
            ],
            "created_at": lineage.created_at.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record lineage: {e}")


@router.get("/renders/{render_id}/lineage")
def get_render_lineage(render_id: str) -> Dict[str, Any]:
    """
    Get the lineage (asset versions used) of a render.
    
    Args:
        render_id: Render artifact ID
    
    Returns:
        RenderLineage data
    """
    try:
        from engines.image_core.versioning import get_versioning_service
        
        svc = get_versioning_service()
        lineage = svc.get_render_lineage(render_id)
        
        if not lineage:
            raise HTTPException(status_code=404, detail=f"Lineage not found for render '{render_id}'")
        
        return {
            "render_id": lineage.render_id,
            "composition_id": lineage.composition_id,
            "created_at": lineage.created_at.isoformat(),
            "assets_used": [
                {
                    "asset_id": entry.asset_id,
                    "version_number": entry.version_number,
                    "layer_id": entry.layer_id,
                    "file_hash": entry.file_hash
                }
                for entry in lineage.assets_used
            ],
            "composition_hash": lineage.composition_hash,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get lineage: {e}")


@router.get("/assets/{asset_id}/renders")
def get_renders_using_asset(
    asset_id: str,
    version_number: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Find all renders that used a specific asset (optionally a specific version).
    
    Args:
        asset_id: Asset identifier
        version_number: Optional specific version
    
    Returns:
        List of renders using the asset
    """
    try:
        from engines.image_core.versioning import get_versioning_service
        
        svc = get_versioning_service()
        renders = svc.get_renders_using_asset(asset_id, version_number)
        
        return {
            "asset_id": asset_id,
            "version_number": version_number,
            "renders": [
                {
                    "render_id": lineage.render_id,
                    "composition_id": lineage.composition_id,
                    "created_at": lineage.created_at.isoformat(),
                    "version_used": lineage.get_asset_versions(asset_id)
                }
                for lineage in renders
            ],
            "total_renders": len(renders)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to find renders: {e}")


@router.post("/assets/{asset_id}/versions/compare")
def compare_asset_versions(
    asset_id: str,
    version_a: int,
    version_b: int,
) -> Dict[str, Any]:
    """
    Compare two versions of an asset.
    
    Args:
        asset_id: Asset identifier
        version_a: First version number
        version_b: Second version number
    
    Returns:
        Comparison data (content diff, size change, metadata changes)
    """
    try:
        from engines.image_core.versioning import get_versioning_service
        
        svc = get_versioning_service()
        comparison = svc.compare_versions(asset_id, version_a, version_b)
        
        if not comparison:
            raise HTTPException(status_code=404, detail=f"Could not compare versions")
        
        return {
            "asset_id": comparison.asset_id,
            "version_a": comparison.version_a,
            "version_b": comparison.version_b,
            "content_different": comparison.content_different,
            "file_hash_a": comparison.file_hash_a,
            "file_hash_b": comparison.file_hash_b,
            "size_a": comparison.size_a,
            "size_b": comparison.size_b,
            "size_change_percent": comparison.size_change_percent,
            "metadata_changes": comparison.metadata_changes,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compare versions: {e}")


# --- Composition Diffing Endpoints ---


@router.post("/compositions/compare")
def compare_compositions(comp_a: ImageComposition, comp_b: ImageComposition) -> Dict[str, Any]:
    """
    Compare two compositions and generate detailed diff report.
    
    Args:
        comp_a: First composition to compare
        comp_b: Second composition to compare
    
    Returns:
        Diff report with layer changes, property changes, and similarity score
    """
    try:
        from engines.image_core.diffing import CompositionDiffer
        
        diff = CompositionDiffer.compare_compositions(comp_a, comp_b)
        
        return {
            "width_a": diff.width_a,
            "height_a": diff.height_a,
            "width_b": diff.width_b,
            "height_b": diff.height_b,
            "background_color_a": diff.background_color_a,
            "background_color_b": diff.background_color_b,
            "total_changes": diff.total_changes,
            "similarity_score": diff.similarity_score,
            "layer_diffs": [
                {
                    "layer_id": ld.layer_id,
                    "layer_name": ld.layer_name,
                    "diff_type": ld.diff_type.value,
                    "property_name": ld.property_name,
                    "old_value": ld.old_value,
                    "new_value": ld.new_value,
                    "description": ld.description,
                }
                for ld in diff.layer_diffs
            ],
            "properties_changed": {
                k: [str(v[0]), str(v[1])]
                for k, v in diff.properties_changed.items()
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compare compositions: {e}")


@router.get("/renders/{render_id_a}/diff/{render_id_b}")
def compare_render_artifacts(render_id_a: str, render_id_b: str) -> Dict[str, Any]:
    """
    Compare two rendered artifacts by ID.
    
    Args:
        render_id_a: First render ID
        render_id_b: Second render ID
    
    Returns:
        Comparison data including pixel hash match, dimension changes
    """
    try:
        from engines.image_core.diffing import CompositionDiffer
        
        # In production, retrieve actual render data from storage
        # For now, return a structured diff response
        
        # This would typically:
        # 1. Load render artifacts from storage (cache/blob)
        # 2. Compute or retrieve pixel hashes
        # 3. Compare dimensions
        # 4. Return comprehensive diff
        
        return {
            "render_id_a": render_id_a,
            "render_id_b": render_id_b,
            "hashes_match": False,
            "content_identical": False,
            "similarity": 0.0,
            "dimension_changes": None,
            "note": "Render comparison requires artifact retrieval from storage"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compare renders: {e}")


@router.post("/artifacts/compare-hashes")
def compare_pixel_hashes(hash_a: str, hash_b: str) -> Dict[str, Any]:
    """
    Compare two render artifact pixel hashes.
    
    Args:
        hash_a: First artifact hash
        hash_b: Second artifact hash
    
    Returns:
        Hash comparison results including match status and similarity
    """
    try:
        from engines.image_core.diffing import CompositionDiffer
        
        result = CompositionDiffer.compare_pixel_hashes(hash_a, hash_b)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compare hashes: {e}")


@router.post("/artifacts/compare-dimensions")
def compare_artifact_dimensions(width_a: int, height_a: int, width_b: int, height_b: int) -> Dict[str, Any]:
    """
    Compare dimensions between two artifacts.
    
    Args:
        width_a: First artifact width
        height_a: First artifact height
        width_b: Second artifact width
        height_b: Second artifact height
    
    Returns:
        Dimension comparison with absolute and percentage changes
    """
    try:
        from engines.image_core.diffing import CompositionDiffer
        
        result = CompositionDiffer.compare_artifact_dimensions(
            width_a, height_a,
            width_b, height_b
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compare dimensions: {e}")


# --- Color Extraction Endpoints ---


@router.post("/compositions/extract-colors")
def extract_colors_from_composition(composition: ImageComposition) -> Dict[str, Any]:
    """
    Extract color palette from composition.
    
    Args:
        composition: Composition to analyze
    
    Returns:
        Color palette with primary, secondary, accent colors and all extracted colors
    """
    try:
        from engines.image_core.color_extraction import ColorExtractor
        
        palette = ColorExtractor.extract_from_composition(composition)
        
        return palette.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract colors: {e}")


@router.post("/colors/generate-palettes")
def generate_color_palettes(
    colors: List[str],
    sizes: Optional[List[int]] = None
) -> Dict[int, List[str]]:
    """
    Generate color palettes of different sizes from color list.
    
    Args:
        colors: List of hex colors
        sizes: Palette sizes to generate (default: [3, 5, 8, 12])
    
    Returns:
        Dictionary mapping size to list of colors
    """
    try:
        from engines.image_core.color_extraction import ColorExtractor
        
        if sizes is None:
            sizes = [3, 5, 8, 12]
        
        # Create ColorMetrics for each color
        color_metrics = [ColorExtractor.create_color_metrics(c) for c in colors]
        
        palettes = ColorExtractor.generate_palette_sizes(color_metrics, sizes)
        
        return palettes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate palettes: {e}")


@router.post("/colors/generate-variations")
def generate_color_variations(
    base_color: str,
    variations: Optional[List[Dict[str, int]]] = None
) -> List[Dict[str, Any]]:
    """
    Generate color variations (lighter/darker/saturated/etc) from base color.
    
    Args:
        base_color: Base hex color
        variations: List of variation definitions with adjustments
    
    Returns:
        List of color variations with results
    """
    try:
        from engines.image_core.color_extraction import ColorExtractor
        
        var_list = ColorExtractor.generate_variations(base_color, variations)
        
        return [v.to_dict() for v in var_list]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate variations: {e}")


@router.get("/colors/check-contrast")
def check_wcag_contrast(
    foreground_color: str,
    background_color: str
) -> Dict[str, Any]:
    """
    Check WCAG contrast compliance between two colors.
    
    Args:
        foreground_color: Hex foreground color
        background_color: Hex background color
    
    Returns:
        Contrast report with WCAG compliance levels
    """
    try:
        from engines.image_core.color_extraction import ColorExtractor
        
        report = ColorExtractor.check_contrast_wcag(foreground_color, background_color)
        
        return report.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check contrast: {e}")


@router.post("/colors/find-accessible-contrast")
def find_accessible_contrast(
    base_color: str,
    background_color: str,
    target_ratio: float = 7.0
) -> Dict[str, Any]:
    """
    Find a variation of base_color that meets WCAG contrast requirements.
    
    Args:
        base_color: Base hex color to adjust
        background_color: Background hex color
        target_ratio: Target contrast ratio (default 7.0 for WCAG AAA)
    
    Returns:
        Recommended color that meets contrast ratio, or None if not found
    """
    try:
        from engines.image_core.color_extraction import ColorExtractor
        
        result_color = ColorExtractor.find_accessible_contrast(
            base_color, background_color, target_ratio
        )
        
        if result_color:
            report = ColorExtractor.check_contrast_wcag(result_color, background_color)
            return {
                "original_color": base_color,
                "adjusted_color": result_color,
                "target_ratio": target_ratio,
                "achieved_ratio": report.contrast_ratio,
                "meets_target": report.contrast_ratio >= target_ratio,
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Could not find variation of {base_color} meeting ratio {target_ratio}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to find accessible contrast: {e}")


# --- Responsive Design Endpoints ---


@router.post("/compositions/make-responsive")
def make_composition_responsive(composition: ImageComposition) -> Dict[str, Any]:
    """
    Convert regular composition to responsive composition.
    
    Args:
        composition: Base composition to make responsive
    
    Returns:
        Responsive composition with layer configurations
    """
    try:
        from engines.image_core.responsive_design import ResponsiveDesignEngine
        
        responsive = ResponsiveDesignEngine.create_responsive_composition(composition)
        
        return responsive.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to make composition responsive: {e}")


@router.post("/responsive/generate-variants")
def generate_responsive_variants(
    composition: ImageComposition,
    include_viewports: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Generate responsive design variants for all viewports.
    
    Args:
        composition: Base composition
        include_viewports: Specific viewport names to include (optional)
    
    Returns:
        List of responsive variants for each viewport
    """
    try:
        from engines.image_core.responsive_design import (
            ResponsiveDesignEngine, ViewportConfig, ViewportSize
        )
        
        responsive = ResponsiveDesignEngine.create_responsive_composition(composition)
        
        # Filter viewports if specified
        if include_viewports:
            all_viewports = responsive.get_default_viewports()
            viewport_map = {v.name.value: v for v in all_viewports}
            viewports = [viewport_map[name] for name in include_viewports if name in viewport_map]
        else:
            viewports = None
        
        variants = ResponsiveDesignEngine.generate_variants(responsive, viewports)
        
        return [v.to_dict() for v in variants]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate variants: {e}")


@router.get("/responsive/image-sizes")
def get_responsive_image_sizes(base_width: int = 1920) -> Dict[str, int]:
    """
    Get recommended image sizes for responsive design srcset.
    
    Args:
        base_width: Base/desktop width (default 1920)
    
    Returns:
        Dictionary of size names to pixel widths
    """
    try:
        from engines.image_core.responsive_design import ResponsiveDesignEngine
        
        return ResponsiveDesignEngine.get_responsive_images_sizes(base_width)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get image sizes: {e}")


@router.get("/responsive/breakpoint-guides")
def get_breakpoint_guides(
    composition: ImageComposition
) -> List[Dict[str, Any]]:
    """
    Get design guides for all breakpoints.
    
    Args:
        composition: Base composition to analyze
    
    Returns:
        List of breakpoint guides with recommendations
    """
    try:
        from engines.image_core.responsive_design import ResponsiveDesignEngine
        
        responsive = ResponsiveDesignEngine.create_responsive_composition(composition)
        viewports = responsive.get_default_viewports()
        
        guides = []
        for viewport in viewports:
            guide = ResponsiveDesignEngine.generate_breakpoint_guide(responsive, viewport)
            guides.append(guide.to_dict())
        
        return guides
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate guides: {e}")


@router.get("/responsive/css-media-queries")
def generate_media_queries(
    composition: ImageComposition
) -> Dict[str, str]:
    """
    Generate CSS media queries for responsive design.
    
    Args:
        composition: Base composition
    
    Returns:
        Dictionary mapping viewport names to CSS media queries
    """
    try:
        from engines.image_core.responsive_design import ResponsiveDesignEngine
        
        responsive = ResponsiveDesignEngine.create_responsive_composition(composition)
        
        return ResponsiveDesignEngine.generate_css_media_queries(responsive)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate media queries: {e}")


@router.get("/responsive/tailwind-breakpoints")
def get_tailwind_config() -> Dict[str, str]:
    """
    Get Tailwind CSS breakpoint configuration.
    
    Returns:
        Dictionary of breakpoint names to pixel widths
    """
    try:
        from engines.image_core.responsive_design import ResponsiveDesignEngine
        
        return ResponsiveDesignEngine.get_tailwindcss_breakpoints()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Tailwind config: {e}")


@router.post("/responsive/layer-density")
def analyze_layer_density(composition: ImageComposition) -> Dict[str, float]:
    """
    Analyze layer density (complexity) across breakpoints.
    
    Args:
        composition: Base composition
    
    Returns:
        Dictionary mapping viewport names to density scores
    """
    try:
        from engines.image_core.responsive_design import ResponsiveDesignEngine
        
        responsive = ResponsiveDesignEngine.create_responsive_composition(composition)
        
        return ResponsiveDesignEngine.analyze_layer_density(responsive)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze density: {e}")
