from __future__ import annotations
import httpx
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore

class ListJoorDesignersInput(BaseModel):
    page: int = 1

class GetJoorLinesheetInput(BaseModel):
    designer_id: str
    season_code: Optional[str] = None

async def _get_client(ctx: RequestContext) -> httpx.AsyncClient:
    secrets = LocalSecretStore()
    api_token = secrets.get_secret(f"joor-token-{ctx.tenant_id}") or secrets.get_secret("joor-token")
    
    if not api_token:
        raise ValueError("Missing 'joor-token' in secrets.")

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
        
    return httpx.AsyncClient(headers=headers, base_url="https://api.jooraccess.com/v2")

async def list_designers(ctx: RequestContext, input_data: ListJoorDesignersInput) -> Dict[str, Any]:
    async with await _get_client(ctx) as client:
        params = {"page": input_data.page}
        response = await client.get("/designers", params=params)
        response.raise_for_status()
        return response.json()

async def get_linesheet(ctx: RequestContext, input_data: GetJoorLinesheetInput) -> Dict[str, Any]:
    async with await _get_client(ctx) as client:
        params = {"designer_id": input_data.designer_id}
        if input_data.season_code:
            params["season"] = input_data.season_code
            
        response = await client.get("/linesheets", params=params)
        response.raise_for_status()
        return response.json()
