from __future__ import annotations

from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException

from engines.common.identity import RequestContext, get_request_context
from engines.common.error_envelope import error_response
from engines.identity.auth import get_auth_context, require_tenant_membership, require_tenant_role
from engines.workbench.store import VersionedStore
# from engines.workbench.publisher import PublisherService # Imported locally in endpoint to avoid circularity if any
# Or just remove the bad import

# Actually UNIFY-ENG-005 says "Expose publisher". The file `engines/workbench/publisher.py` exists (step 20).

router = APIRouter(prefix="/workbench", tags=["workbench"])

_store = VersionedStore() # Default

@router.put("/drafts/{tool_name}")
def save_draft(
    tool_name: str,
    payload: Dict[str, Any],
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    # Payload is "MCPToolDefinition" usually.
    # Enforce basic validation?
    try:
        if payload.get("name") != tool_name:
             # Basic consistency check, or just overwrite name?
             pass 
        _store.put_draft(context, tool_name, payload)
        return {"status": "saved", "tool": tool_name}
    except Exception as exc:
        error_response(
            code="workbench.draft_save_failed",
            message=str(exc),
            status_code=500,
            resource_kind="workbench_store",
        )

@router.get("/drafts/{tool_name}")
def get_draft(
    tool_name: str,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    try:
        item = _store.get_draft(context, tool_name)
        if not item:
            # 404
            raise HTTPException(status_code=404, detail="Draft not found")
        return item.data
    except HTTPException:
        raise
    except Exception as exc:
        error_response(
            code="workbench.draft_read_failed",
            message=str(exc),
            status_code=500,
            resource_kind="workbench_store",
        )

@router.get("/drafts")
def list_drafts(
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    try:
        items = _store.list_all_drafts(context)
        # Return simplified list
        return [
            {
                "id": item.key, # tool_name is id
                "updated_at": item.updated_at.isoformat(),
                "version": item.version,
                "name": item.data.get("name"),
            }
            for item in items
        ]
    except Exception as exc:
        error_response(
            code="workbench.draft_list_failed",
            message=str(exc),
            status_code=500,
            resource_kind="workbench_store",
        )

# UNIFY-ENG-005: Publish Endpoint
@router.post("/publish")
def publish_tool(
    payload: Dict[str, Any], # { "tool_id": "...", "draft_version": "..." }
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    
    # 1. Get Draft
    tool_id = payload.get("tool_id") or payload.get("name") # UI sends name as ID sometimes?
    if not tool_id:
        error_response("validation.missing_field", "tool_id required", 400)
        
    try:
        from engines.workbench.publisher import get_publisher_service
        from engines.workbench.models import PortableMCPPackage, NorthstarActivationOverlay, ToolDefinition, ToolOverlay, ScopeOverlay, PolicyConfig
        
        draft = _store.get_draft(context, tool_id)
        if not draft:
            error_response("workbench.draft_missing", f"No draft for {tool_id}", 404)
        
        data = draft.data # The JSON draft from UI
        
        # 2. Version Check
        # UI Draft: { name: "...", version: "1.0.0", scopes: [...] }
        version = data.get("version")
        if not version or version == "draft":
            error_response("validation.invalid_version", "Draft must have concrete version", 400)
        
        # 3. Map to Portable Package (Layer 1)
        # UI assumes "One Tool Definition" per Workbench Draft usually, but let's map carefully.
        # Ensure we have a list of definitions even if UI sends flat structure?
        # Actually UI `MCPToolDefinition` is one tool.
        
        # Build one ToolDefinition
        t_id = data.get("name")
        t_scopes = {}
        
        # Map Scopes from Draft
        # draft.scopes list: { scope_name, description, ... }
        draft_scopes = data.get("scopes", [])
        for s in draft_scopes:
            s_name = s.get("scope_name")
            # s_schema = s.get("input_schema") # If UI sends it
            t_scopes[s_name] = {} # Schema stub if not provided
            
        tool_def = ToolDefinition(
            id=t_id,
            name=data.get("name"),
            summary=data.get("description", ""),
            scopes=t_scopes
        )
        
        package = PortableMCPPackage(
            id=f"{t_id}", # Package ID = Tool ID for simple connector
            version=version,
            name=data.get("name"),
            description=data.get("description", ""),
            tools=[tool_def]
        )
        
        # 4. Map to Overlay (Layer 2)
        tool_overlays = {}
        scope_overlays = {}
        
        for s in draft_scopes:
            s_name = s.get("scope_name")
            policy = PolicyConfig(
                firearms=s.get("requires_firearms", False),
                required_licenses=s.get("required_license_types", [])
            )
            scope_overlays[s_name] = ScopeOverlay(policy=policy)
            
        tool_overlays[t_id] = ToolOverlay(scopes=scope_overlays)
        
        overlay = NorthstarActivationOverlay(
            package_id=package.id,
            package_version=package.version,
            tools=tool_overlays
        )

        # 5. Publish via Service
        publisher = get_publisher_service()
        publisher.publish(context, package, overlay)

        # 6. Commit Version in Store
        _store.publish(context, tool_id, version)

        return {
             "portable_package": {
                 "package_id": package.id,
                 "version": package.version,
                 "download_url": f"/artifacts/{package.id}/{package.version}/package.json"
             },
             "activation_overlay": {
                 "overlay_id": f"{package.id}.overlay",
                 "version": package.version
             }
        }

    except Exception as exc:
        error_response(
            code="workbench.publish_failed",
            message=str(exc),
            status_code=500,
            resource_kind="workbench_store",
        )
