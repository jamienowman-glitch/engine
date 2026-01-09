from __future__ import annotations
from typing import Dict, Any
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore
from engines.connectors.generic_stdio.impl import StdioMCPAdapter

# --- Input Models ---

class ManageScenesInput(BaseModel):
    pass

class ControlStreamInput(BaseModel):
    action: str = Field(..., description="'start' or 'stop'")

class RawToolInput(BaseModel):
    tool_name: str = Field(..., description="Name of the tool to call")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")

# --- Adapter Logic ---

async def _get_adapter(ctx: RequestContext) -> StdioMCPAdapter:
    secrets = LocalSecretStore()
    
    # Try tenant specific, then generic
    password = secrets.get_secret(f"obs-password-{ctx.tenant_id}") or secrets.get_secret("obs-password")
    
    # Password is optional for OBS if not configured, but recommended
    env_vars = {}
    if password:
        env_vars["OBS_WEBSOCKET_PASSWORD"] = password.strip()

    return StdioMCPAdapter(
        command="npx",
        args=["-y", "obs-mcp@latest"],
        env=env_vars
    )

# --- Handlers ---

async def get_scenes(ctx: RequestContext, input_data: ManageScenesInput) -> Any:
    adapter = await _get_adapter(ctx)
    return await adapter.call_tool("GetSceneList", {})

async def start_stream(ctx: RequestContext, input_data: ControlStreamInput) -> Any:
    adapter = await _get_adapter(ctx)
    tool_name = "StartStream" if input_data.action == "start" else "StopStream"
    return await adapter.call_tool(tool_name, {})
    
async def call_raw_tool(ctx: RequestContext, input_data: RawToolInput) -> Any:
    adapter = await _get_adapter(ctx)
    return await adapter.call_tool(input_data.tool_name, input_data.arguments)
