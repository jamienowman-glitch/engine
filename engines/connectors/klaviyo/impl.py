from __future__ import annotations
from typing import Dict, Any
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore
from engines.connectors.generic_stdio.impl import StdioMCPAdapter

# --- Input Models ---

class GetAccountDetailsInput(BaseModel):
    pass

class GetCampaignsInput(BaseModel):
    pass

class GetMetricsInput(BaseModel):
    pass

class RawToolInput(BaseModel):
    tool_name: str = Field(..., description="Name of the tool to call")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")

# --- Adapter Logic ---

async def _get_adapter(ctx: RequestContext) -> StdioMCPAdapter:
    secrets = LocalSecretStore()
    
    # Try tenant specific, then generic
    api_key = secrets.get_secret(f"klaviyo-api-key-{ctx.tenant_id}") or secrets.get_secret("klaviyo-api-key")
    
    if not api_key:
        raise ValueError("Missing 'klaviyo-api-key' in secrets. Please configure it in the Workbench.")

    return StdioMCPAdapter(
        command="uvx",
        args=["klaviyo-mcp-server@latest"],
        env={
            "PRIVATE_API_KEY": api_key.strip(),
            "READ_ONLY": "false",
            "ALLOW_USER_GENERATED_CONTENT": "false"
        }
    )

# --- Handlers ---

async def get_account_details(ctx: RequestContext, input_data: GetAccountDetailsInput) -> Any:
    adapter = await _get_adapter(ctx)
    return await adapter.call_tool("get_account_details", {})

async def get_campaigns(ctx: RequestContext, input_data: GetCampaignsInput) -> Any:
    adapter = await _get_adapter(ctx)
    return await adapter.call_tool("get_campaigns", {})

async def get_metrics(ctx: RequestContext, input_data: GetMetricsInput) -> Any:
    adapter = await _get_adapter(ctx)
    return await adapter.call_tool("get_metrics", {})
    
async def call_raw_tool(ctx: RequestContext, input_data: RawToolInput) -> Any:
    adapter = await _get_adapter(ctx)
    return await adapter.call_tool(input_data.tool_name, input_data.arguments)
