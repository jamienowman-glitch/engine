from __future__ import annotations
import httpx
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore

class SearchFashionGoInput(BaseModel):
    keyword: str
    category: Optional[str] = None
    page: int = 1

async def _get_client(ctx: RequestContext) -> httpx.AsyncClient:
    secrets = LocalSecretStore()
    api_token = secrets.get_secret(f"fashiongo-token-{ctx.tenant_id}") or secrets.get_secret("fashiongo-token")
    
    if not api_token:
        raise ValueError("Missing 'fashiongo-token' in secrets.")

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
        
    return httpx.AsyncClient(headers=headers, base_url="https://api.fashiongo.net")

async def search_apparel(ctx: RequestContext, input_data: SearchFashionGoInput) -> Dict[str, Any]:
    async with await _get_client(ctx) as client:
        params = {"q": input_data.keyword, "page": input_data.page}
        if input_data.category:
            params["category"] = input_data.category
            
        response = await client.get("/v1/items", params=params)
        response.raise_for_status()
        return response.json()
