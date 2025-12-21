"""Template models for composition reuse and variable substitution."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator


class TemplateVariable(BaseModel):
    """A variable placeholder in a template."""
    name: str = Field(..., description="Variable name (e.g., 'product_name')")
    placeholder: str = Field(..., description="Placeholder syntax (e.g., '$product_name')")
    type: str = Field(..., description="Type: text, asset, color, number")
    required: bool = Field(default=True, description="Is this variable required?")
    default: Optional[str] = Field(None, description="Default value if not provided")


class CompositionTemplate(BaseModel):
    """Reusable composition template with variable substitution."""
    template_id: str = Field(..., description="Unique template ID")
    name: str = Field(..., description="Human-readable template name")
    description: Optional[str] = Field(None, description="Template description")
    tenant_id: str = Field(..., description="Tenant ID (for multi-tenant support)")
    version: int = Field(default=1, description="Template version")
    
    # Template composition structure
    width: int = Field(..., description="Canvas width")
    height: int = Field(..., description="Canvas height")
    background_color: str = Field(default="#FFFFFF", description="Background color")
    layers_template: List[Dict[str, Any]] = Field(..., description="Layer templates with variables")
    
    # Variables supported in this template
    variables: List[TemplateVariable] = Field(default_factory=list, description="Variables in template")
    
    # Metadata
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    category: Optional[str] = Field(None, description="Template category (social, email, print, etc)")
    tags: List[str] = Field(default_factory=list, description="Tags for discovery")

    @field_validator("template_id")
    @classmethod
    def validate_template_id(cls, v):
        if not v or not v.strip():
            raise ValueError("template_id cannot be empty")
        return v


class RenderFromTemplateRequest(BaseModel):
    """Request to render from a template with variable substitution."""
    template_id: str = Field(..., description="Template ID to use")
    tenant_id: str = Field(..., description="Tenant ID")
    env: str = Field(..., description="Environment (dev/test/prod)")
    variables: Dict[str, Any] = Field(..., description="Variable values (name → value)")
    preset_id: Optional[str] = Field(None, description="Export preset ID")
    parent_asset_id: Optional[str] = Field(None, description="Parent asset ID")

    @field_validator("variables")
    @classmethod
    def validate_variables(cls, v):
        if not v:
            raise ValueError("variables cannot be empty")
        return v
