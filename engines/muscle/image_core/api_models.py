"""API request/response models for image_core HTTP endpoints."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class RenderCompositionRequest(BaseModel):
    """Request to render a composition."""
    tenant_id: str = Field(..., description="Tenant ID")
    env: str = Field(..., description="Environment (dev/test/prod)")
    composition: Dict[str, Any] = Field(..., description="Composition JSON (width, height, layers, etc)")
    preset_id: Optional[str] = Field(None, description="Export preset ID (e.g., 'instagram_1080')")
    parent_asset_id: Optional[str] = Field(None, description="Parent asset ID for tracking")

    @field_validator("tenant_id")
    @classmethod
    def validate_tenant_id(cls, v):
        if not v or not v.strip():
            raise ValueError("tenant_id cannot be empty")
        return v

    @field_validator("env")
    @classmethod
    def validate_env(cls, v):
        if v not in {"dev", "test", "prod", "local"}:
            raise ValueError("env must be one of: dev, test, prod, local")
        return v


class BatchRenderRequest(BaseModel):
    """Request to render a composition with multiple presets."""
    tenant_id: str = Field(..., description="Tenant ID")
    env: str = Field(..., description="Environment")
    composition: Dict[str, Any] = Field(..., description="Composition JSON")
    preset_ids: List[str] = Field(default_factory=list, description="List of preset IDs to render")

    @field_validator("preset_ids")
    @classmethod
    def validate_presets(cls, v):
        if not v:
            raise ValueError("preset_ids cannot be empty")
        if len(v) > 20:
            raise ValueError("Too many presets (max 20)")
        return v


class RenderResponse(BaseModel):
    """Response from render endpoint."""
    artifact_id: str = Field(..., description="ID of the created artifact")
    format: str = Field(..., description="Output format (PNG, JPEG, WEBP, TIFF)")
    width: int = Field(..., description="Output width in pixels")
    height: int = Field(..., description="Output height in pixels")
    preset_id: Optional[str] = Field(None, description="Preset used")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Artifact metadata")


class BatchRenderResponse(BaseModel):
    """Response from batch render endpoint."""
    results: Dict[str, RenderResponse] = Field(..., description="Map of preset_id → RenderResponse")
    total_count: int = Field(..., description="Total presets rendered")


class PresetInfo(BaseModel):
    """Information about a single preset."""
    preset_id: str = Field(..., description="Preset ID")
    format: str = Field(..., description="Output format")
    width: Optional[int] = Field(None, description="Target width")
    height: Optional[int] = Field(None, description="Target height")
    quality: Optional[int] = Field(None, description="Quality (0-100)")
    dpi: Optional[int] = Field(None, description="DPI for print presets")
    category: str = Field(..., description="Preset category (web, social, print, etc)")


class PresetsListResponse(BaseModel):
    """Response listing all available presets."""
    presets: List[PresetInfo] = Field(..., description="List of available presets")
    total_count: int = Field(..., description="Total number of presets")
