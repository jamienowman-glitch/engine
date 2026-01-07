from typing import Optional, List
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext, assert_context_matches
from engines.mcp_gateway.inventory import Tool, Scope
# Import from muscle.media_v2
from engines.media_v2.models import MediaAsset, MediaKind
from engines.media_v2.service import get_media_service

class ListAssetsInput(BaseModel):
    kind: Optional[MediaKind] = Field(None, description="Filter by media kind")
    tag: Optional[str] = Field(None, description="Filter by tag")

class GetAssetInput(BaseModel):
    asset_id: str = Field(..., description="Asset to retrieve")

async def list_assets_handler(ctx: RequestContext, args: ListAssetsInput):
    service = get_media_service()
    # In a real tool, we might enforce policy here.
    # The user is already authenticated via RequestContext.
    # Service call requires tenant_id.
    return service.list_assets(
        tenant_id=ctx.tenant_id, 
        kind=args.kind, 
        tag=args.tag
    )

async def get_asset_handler(ctx: RequestContext, args: GetAssetInput):
    service = get_media_service()
    asset = service.get_asset(args.asset_id)
    if not asset:
        # In MCP, we might want to return structured error or just None/empty
        # For now, let's return None implies 404 behavior or empty result? 
        # Or raise HTTPException.
        # But for tools, raising exception is caught by the tool runner.
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Check tenant ownership
    if asset.tenant_id != ctx.tenant_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Asset not found") # 404 for security
        
    return asset

def register(inventory):
    tool = Tool(
        id="media_v2",
        name="Media V2",
        summary="Manage media assets"
    )
    
    tool.register_scope(Scope(
        name="media_v2.list",
        description="List media assets",
        input_model=ListAssetsInput,
        handler=list_assets_handler
    ))
    
    tool.register_scope(Scope(
        name="media_v2.get",
        description="Get a single media asset",
        input_model=GetAssetInput,
        handler=get_asset_handler
    ))
    
    inventory.register_tool(tool)
