from __future__ import annotations
import httpx
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore

class SearchTundraInput(BaseModel):
    query: str
    page: int = 1

async def _get_client(ctx: RequestContext) -> httpx.AsyncClient:
    secrets = LocalSecretStore()
    api_token = secrets.get_secret(f"tundra-token-{ctx.tenant_id}") or secrets.get_secret("tundra-token")
    
    if not api_token:
        raise ValueError("Missing 'tundra-token' in secrets.")

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
        
    return httpx.AsyncClient(headers=headers, base_url="https://www.tundra.com/api")

async def search_wholesale(ctx: RequestContext, input_data: SearchTundraInput) -> Dict[str, Any]:
    async with await _get_client(ctx) as client:
        params = {"q": input_data.query, "page": input_data.page}
        response = await client.get("/v2/products", params=params)
        response.raise_for_status()
        return response.json()
