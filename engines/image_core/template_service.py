"""Template service for composition reuse and variable substitution."""

from typing import Dict, List, Optional, Any
import json
import re
from datetime import datetime

from engines.image_core.models import ImageComposition, ImageLayer
from engines.image_core.template_models import CompositionTemplate, TemplateVariable
from engines.image_core.service import ImageCoreService


class TemplateService:
    """Manages reusable composition templates with variable substitution."""
    
    def __init__(self):
        """Initialize template storage (in-memory; could be persisted to DB)."""
        self._templates: Dict[str, CompositionTemplate] = {}

    def save_template(self, template: CompositionTemplate) -> CompositionTemplate:
        """Save a template for reuse."""
        self._templates[template.template_id] = template
        return template

    def get_template(self, template_id: str) -> Optional[CompositionTemplate]:
        """Retrieve a template by ID."""
        return self._templates.get(template_id)

    def list_templates(self, tenant_id: str, category: Optional[str] = None) -> List[CompositionTemplate]:
        """List templates for a tenant, optionally filtered by category."""
        templates = [t for t in self._templates.values() if t.tenant_id == tenant_id]
        if category:
            templates = [t for t in templates if t.category == category]
        return templates

    def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False

    def _substitute_variables(self, text: str, variables: Dict[str, Any]) -> str:
        """Replace $variable placeholders with actual values."""
        result = text
        for var_name, var_value in variables.items():
            placeholder = f"${var_name}"
            # Convert value to string if needed
            var_str = str(var_value) if var_value is not None else ""
            result = result.replace(placeholder, var_str)
        return result

    def _process_layer_template(self, layer_template: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
        """Process a layer template, substituting variables."""
        layer = layer_template.copy()
        
        # Substitute in text fields
        for key in ["name", "text", "color", "background_color"]:
            if key in layer and isinstance(layer[key], str):
                layer[key] = self._substitute_variables(layer[key], variables)
        
        # Handle asset references
        if "asset_var" in layer:
            asset_var = layer.pop("asset_var")
            if asset_var in variables:
                layer["asset_id"] = variables[asset_var]
        
        return layer

    def render_from_template(
        self,
        template_id: str,
        tenant_id: str,
        env: str,
        variables: Dict[str, Any],
        image_service: ImageCoreService,
        preset_id: Optional[str] = None,
        parent_asset_id: Optional[str] = None,
    ) -> str:
        """
        Render a composition from a template with variable substitution.
        
        Args:
            template_id: Template to use
            tenant_id: Tenant ID
            env: Environment
            variables: Variable values
            image_service: ImageCoreService instance
            preset_id: Optional export preset
            parent_asset_id: Optional parent asset ID
            
        Returns:
            Artifact ID of rendered composition
        """
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        # Validate required variables
        required_vars = {v.name for v in template.variables if v.required}
        provided_vars = set(variables.keys())
        missing_vars = required_vars - provided_vars
        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")
        
        # Add defaults for optional variables
        final_vars = variables.copy()
        for var in template.variables:
            if var.name not in final_vars and var.default:
                final_vars[var.name] = var.default
        
        # Process layers
        layers = []
        for layer_template in template.layers_template:
            processed = self._process_layer_template(layer_template, final_vars)
            try:
                layer = ImageLayer(**processed)
                layers.append(layer)
            except Exception as e:
                raise ValueError(f"Failed to process layer template: {e}")
        
        # Create composition
        comp = ImageComposition(
            tenant_id=tenant_id,
            env=env,
            width=template.width,
            height=template.height,
            background_color=template.background_color,
            layers=layers,
        )
        
        # Render and return artifact ID
        artifact_id = image_service.render_composition(
            comp,
            parent_asset_id=parent_asset_id,
            preset_id=preset_id,
        )
        
        return artifact_id


# Module-level singleton
_default_template_service: Optional[TemplateService] = None


def get_template_service() -> TemplateService:
    """Get or create the default template service."""
    global _default_template_service
    if _default_template_service is None:
        _default_template_service = TemplateService()
    return _default_template_service
