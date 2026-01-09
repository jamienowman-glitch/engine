from __future__ import annotations
import httpx
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore

# --- Input Models ---

class SearchDHgateInput(BaseModel):
    keyword: str
    category_id: Optional[str] = None
    page_no: int = 1
    page_size: int = 20

class GetDHgateProductInput(BaseModel):
    item_code: str = Field(..., description="DHgate Item Code")

# --- Connector Logic ---

async def _get_client(ctx: RequestContext) -> httpx.AsyncClient:
    secrets = LocalSecretStore()
    
    api_token = secrets.get_secret(f"dhgate-token-{ctx.tenant_id}") or secrets.get_secret("dhgate-token")
    
    if not api_token:
        raise ValueError("Missing 'dhgate-token' in secrets.")

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
        
    return httpx.AsyncClient(headers=headers, base_url="https://api.dhgate.com/v1")

# --- Handlers ---

async def search_products(ctx: RequestContext, input_data: SearchDHgateInput) -> Dict[str, Any]:
    async with await _get_client(ctx) as client:
        params = {
            "q": input_data.keyword,
            "pageNo": input_data.page_no,
            "pageSize": input_data.page_size
        }
        if input_data.category_id:
            params["cid"] = input_data.category_id
            
        # Assuming REST path based on method names
        response = await client.get("/search/list", params=params)
        response.raise_for_status()
        return response.json()

async def get_product(ctx: RequestContext, input_data: GetDHgateProductInput) -> Dict[str, Any]:
    async with await _get_client(ctx) as client:
        params = {"itemCode": input_data.item_code}
        response = await client.get("/product/get", params=params)
        response.raise_for_status()
        return response.json()
