from __future__ import annotations
import os
import shutil
import subprocess
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore
from engines.connectors.generic_stdio.impl import StdioMCPAdapter

# --- Input Models ---

class ReadActivityInput(BaseModel):
    activity_id: int = Field(..., description="The ID of the activity")

class ReadAthleteInput(BaseModel):
    pass

class CreateActivityInput(BaseModel):
    name: str
    sport_type: str
    start_date_local: str
    elapsed_time: int
    distance: float = 0

class RawToolInput(BaseModel):
    tool_name: str = Field(..., description="Name of the tool to call")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")

# --- Adapter Logic ---

def _ensure_driver_installed(driver_path: str):
    """Clones the driver repository if not present."""
    if not os.path.exists(driver_path):
        os.makedirs(os.path.dirname(driver_path), exist_ok=True)
        # Clone the repo
        subprocess.run(
            ["git", "clone", "https://github.com/ctvidic/strava-mcp-server.git", driver_path],
            check=True,
            capture_output=True
        )

async def _get_adapter(ctx: RequestContext) -> StdioMCPAdapter:
    secrets = LocalSecretStore()
    
    # Retrieve secrets (Generic or Tenant Specific)
    client_id = secrets.get_secret("strava-client-id")
    client_secret = secrets.get_secret("strava-client-secret")
    refresh_token = secrets.get_secret("strava-refresh-token")
    
    if not all([client_id, client_secret, refresh_token]):
         raise ValueError("Missing Strava secrets. Please add strava-client-id, strava-client-secret, and strava-refresh-token to Workbench.")

    # Driver Path
    driver_path = os.path.expanduser("~/.northstar/drivers/strava")
    _ensure_driver_installed(driver_path)
    
    # Inject Config
    config_dir = os.path.join(driver_path, "config")
    os.makedirs(config_dir, exist_ok=True)
    env_file = os.path.join(config_dir, ".env")
    
    with open(env_file, "w") as f:
        f.write(f"STRAVA_CLIENT_ID={client_id}\n")
        f.write(f"STRAVA_CLIENT_SECRET={client_secret}\n")
        f.write(f"STRAVA_REFRESH_TOKEN={refresh_token}\n")
        
    # We use `uv run` which handles venv and deps automatically if pyproject.toml is valid.
    # If pyproject.toml is broken (as suspected), we might need to manually install deps.
    # But `uv run` with `--with` is robust.
    # Let's assume the repo's deps are installable via `uv run` context or we explicit them.
    # Given the broken `pyproject.toml` seen earlier, explicitly adding deps is safer.
    
    script_path = os.path.join(driver_path, "src", "strava_server.py")

    return StdioMCPAdapter(
        command="uv",
        args=[
            "run", 
            "--with", "requests", 
            "--with", "python-dotenv", 
            "--with", "mcp", # Likely needed if not in default env
            # Actually, `fastmcp` is used in source.
             "--with", "fastmcp",
            script_path
        ],
        env={}, # Secrets are in the .env file now
    )

async def _execute_with_adapter(ctx: RequestContext, tool_name: str, args: Dict[str, Any]) -> Any:
    adapter = await _get_adapter(ctx)
    return await adapter.call_tool(tool_name, args)

# --- Handlers ---

async def get_activity(ctx: RequestContext, input_data: ReadActivityInput) -> Any:
    return await _execute_with_adapter(ctx, "get_activity", {"activity_id": input_data.activity_id})

async def get_athlete_stats(ctx: RequestContext, input_data: ReadAthleteInput) -> Any:
    return await _execute_with_adapter(ctx, "get_athlete_stats", {})

async def create_activity(ctx: RequestContext, input_data: CreateActivityInput) -> Any:
    return await _execute_with_adapter(ctx, "create_activity", input_data.dict())

async def call_raw_tool(ctx: RequestContext, input_data: RawToolInput) -> Any:
    return await _execute_with_adapter(ctx, input_data.tool_name, input_data.arguments)
