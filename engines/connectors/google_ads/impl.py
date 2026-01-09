from __future__ import annotations
import os
import tempfile
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore
from engines.connectors.generic_stdio.impl import StdioMCPAdapter

# --- Input Models ---

class ListAccountsInput(BaseModel):
    pass

class ExecuteGAQLInput(BaseModel):
    query: str = Field(..., description="The GAQL query to execute (e.g. SELECT campaign.name FROM campaign)")
    customer_id: str = Field(..., description="The Customer ID to query (digits only)")
    login_customer_id: Optional[str] = Field(None, description="Optional MCC login customer ID")

class ReadDocsInput(BaseModel):
    view: Optional[str] = Field(None, description="Specific view name to read docs for, or leave empty for general docs")

class RawToolInput(BaseModel):
    tool_name: str = Field(..., description="Name of the tool to call")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")

# --- Adapter Logic ---

async def _get_adapter(ctx: RequestContext) -> StdioMCPAdapter:
    """
    Creates an adapter for Google Ads.
    Handles the complexity of writing the YAML credential file required by the official MCP server.
    """
    secrets = LocalSecretStore()
    
    # Try tenant specific, then generic
    yaml_content = secrets.get_secret(f"google-ads-yaml-{ctx.tenant_id}") or secrets.get_secret("google-ads-yaml")
    
    if not yaml_content:
        raise ValueError("Missing 'google-ads-yaml' in secrets. Please paste your google-ads.yaml content into the Workbench.")

    # Create a secure temporary file
    # We use delete=False so we can pass the path, but we should Ideally clean it up.
    # For this implementation, we will rely on the OS /tmp cleanup or overwrite the same file per tenant to avoid filling disk.
    # Better yet, let's use a consistent path in the user's secret dir if possible, or a named temp file.
    
    # Using a named temp file in a secure location
    secure_dir = os.path.expanduser("~/.northstar/tmp")
    os.makedirs(secure_dir, exist_ok=True, mode=0o700)
    
    creds_path = os.path.join(secure_dir, f"google-ads-{ctx.tenant_id or 'generic'}.yaml")
    
    # Write the file (0o600 for security)
    with open(creds_path, "w") as f:
        f.write(yaml_content)
    os.chmod(creds_path, 0o600)

    # The command uses `uvx` to run the server from the git repo
    # We use the specific git URL as per documentation
    return StdioMCPAdapter(
        command="uvx",
        args=[
            "--from", "git+https://github.com/google-marketing-solutions/google_ads_mcp.git", 
            "ads_mcp" # Entry point mapping might be needed if uvx doesn't infer it, but docs say 'uv run ...'
            # Docs say: command: uv, args: [run, ...]
            # Let's try to match the "Direct Launch" or "pipx" style but via uvx for portability
            # "uvx --from git+... run-mcp-server" seems to be what `pipx` alias does if we look at `pyproject.toml` (inferred)
            # Actually, looking at docs: "command": "pipx", "args": ["run", "--spec", "git+...", "run-mcp-server"]
            # Let's emulate that with `uvx`.
            # `uvx client` usually installs tool. 
            # If the package exposes a script `run-mcp-server`, `uvx` should find it.
        ],
        env={
            "GOOGLE_ADS_CREDENTIALS": creds_path
        }
    )

async def _execute_with_cleanup_wrapper(ctx: RequestContext, tool_name: str, args: Dict[str, Any]) -> Any:
    """Helper to ensure we define the command args correctly for `uvx` specifically for this repo."""
    # Based on research, the repo is a python project. 
    # Attempt 1: uvx --from git+https://github.com/google-marketing-solutions/google_ads_mcp.git run-mcp-server
    # If `run-mcp-server` is the script name.
    
    # Re-reading research: "command": "pipx", "args": ["run", "--spec", "git+...", "run-mcp-server"]
    # We will try:
    cmd = "uvx"
    cmd_args = [
        "--from", "git+https://github.com/google-marketing-solutions/google_ads_mcp.git",
        "run-mcp-server"
    ]
    
    adapter = await _get_adapter(ctx)
    # Patch the args in the adapter since we refined them here
    adapter.command = cmd
    adapter.args = cmd_args
    
    return await adapter.call_tool(tool_name, args)

# --- Handlers ---

async def list_accessible_accounts(ctx: RequestContext, input_data: ListAccountsInput) -> Any:
    return await _execute_with_cleanup_wrapper(ctx, "list_accessible_accounts", {})

async def execute_gaql(ctx: RequestContext, input_data: ExecuteGAQLInput) -> Any:
    # MCP tool signature: execute_gaql(query: str, customer_id: str, login_customer_id: str | None)
    args = {
        "query": input_data.query,
        "customer_id": input_data.customer_id
    }
    if input_data.login_customer_id:
        args["login_customer_id"] = input_data.login_customer_id
        
    return await _execute_with_cleanup_wrapper(ctx, "execute_gaql", args)

async def read_docs(ctx: RequestContext, input_data: ReadDocsInput) -> Any:
    # This maps to either `get_gaql_doc` or `get_reporting_view_doc`
    # We'll expose `get_reporting_view_doc` as the primary doc reader
    args = {}
    if input_data.view:
        args["view"] = input_data.view
    return await _execute_with_cleanup_wrapper(ctx, "get_reporting_view_doc", args)
    
async def call_raw_tool(ctx: RequestContext, input_data: RawToolInput) -> Any:
    return await _execute_with_cleanup_wrapper(ctx, input_data.tool_name, input_data.arguments)
