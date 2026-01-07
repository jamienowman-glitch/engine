from __future__ import annotations
from typing import Optional

from engines.common.identity import RequestContext
from engines.registry.service import ComponentRegistryService, get_component_registry_service
from engines.firearms.service import FirearmsService, get_firearms_service
from engines.firearms.models import FirearmBinding
from engines.kpi.service import KpiService, get_kpi_service
# Future: from engines.kpi.models import KpiCorridor

from engines.workbench.models import PortableMCPPackage, NorthstarActivationOverlay

class PublisherService:
    def __init__(
        self,
        registry: Optional[ComponentRegistryService] = None,
        firearms: Optional[FirearmsService] = None,
        kpi: Optional[KpiService] = None
    ):
        self.registry = registry or get_component_registry_service()
        self.firearms = firearms or get_firearms_service()
        self.kpi = kpi or get_kpi_service()

    def publish(
        self, 
        ctx: RequestContext, 
        package: PortableMCPPackage, 
        overlay: Optional[NorthstarActivationOverlay] = None
    ) -> None:
        """
        Publishes a Portable Package and an optional Activation Overlay.
        1. Package -> ComponentRegistry (as Spec)
        2. Overlay -> FirearmsService (Bindings) & KpiService (Bindings)
        """
        
        # 1. Publish Package Spec
        # metadata.spec_class="mcp_connector" distinguishes this component
        component_payload = {
            "id": package.id,
            "version": 1, # TODO: parse package.version? Registry uses int version.
            "schema": package.model_dump(mode="json"),
            "defaults": {}, # Could store default config here
            "metadata": {
                "spec_class": "mcp_connector",
                "package_version": package.version,
                "name": package.name,
                "description": package.description
            }
        }
        self.registry.save_component(ctx, component_payload)
        
        # 2. Process Overlay
        if overlay:
            self._apply_overlay(ctx, package, overlay)

    def _apply_overlay(
        self, 
        ctx: RequestContext, 
        package: PortableMCPPackage, 
        overlay: NorthstarActivationOverlay
    ) -> None:
        
        # Overlay maps keys (tool_id) -> content
        for tool_id, tool_overlay in overlay.tools.items():
            for scope_name, scope_content in tool_overlay.scopes.items():
                
                # Construct Action ID for enforcement: "{tool_id}.{scope_name}"
                action_id = f"{tool_id}.{scope_name}"
                
                # A. Firearms Binding
                if scope_content.policy and scope_content.policy.firearms:
                   # For each required license, create a binding?
                   # Firearms Binding model has `firearm_id` and `action`.
                   # If multiple licenses are required, we might need multiple bindings or a composite firearm key.
                   # For Phase 3, we'll assume one primary firearm requirement or just "requires_firearms".
                   # Model allows `required_licenses` list.
                   # But binding logic usually binds Action -> 1 Firearm ID?
                   # Let's check FirearmBinding definition.
                   # Assuming 1:1 for now. If multiple, assume first is the "Key" firearm.
                   
                   licenses = scope_content.policy.required_licenses
                   if not licenses:
                       # If firearms=True but no specific license listed, imply a generic one?
                       licenses = ["firearms.general"]
                       
                   for lic in licenses:
                       binding = FirearmBinding(
                           action_name=action_id,
                           firearm_id=lic,
                           strategy_lock_required=False # Configurable?
                       )
                       self.firearms.bind_action(ctx, binding)
                       
                # B. KPI Binding (Future)
                # if scope_content.kpi_impact:
                #    ...


_default_service: Optional[PublisherService] = None

def get_publisher_service() -> PublisherService:
    global _default_service
    if _default_service is None:
        _default_service = PublisherService()
    return _default_service
