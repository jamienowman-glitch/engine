from __future__ import annotations
import httpx
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore

# --- Input Models ---

class CalculateAliFreightInput(BaseModel):
    product_id: str
    country_code: str
    product_num: int = 1
    province_code: Optional[str] = None
    city_code: Optional[str] = None

# --- Connector Logic ---

async def _get_client(ctx: RequestContext) -> httpx.AsyncClient:
    secrets = LocalSecretStore()
    
    api_token = secrets.get_secret(f"aliexpress-token-{ctx.tenant_id}") or secrets.get_secret("aliexpress-token")
    
    if not api_token:
        raise ValueError("Missing 'aliexpress-token' in secrets.")

    # AliExpress Open Platform usually passes access_token as a query param or body field
    # We'll attach it to the client default params for simplicity
    
    return httpx.AsyncClient(
        params={"access_token": api_token},
        base_url="https://api-sg.aliexpress.com"
    )

# --- Handlers ---

async def calculate_freight(ctx: RequestContext, input_data: CalculateAliFreightInput) -> Dict[str, Any]:
    async with await _get_client(ctx) as client:
        # Structure for AliExpress Dropshipping API (aliexpress.logistics.buyer.freight.calculate)
        # Usually accepts a JSON string in 'param_aeop_freight_calculate_for_buyer_d_t_o'
        
        dto = {
            "product_id": input_data.product_id,
            "country_code": input_data.country_code,
            "product_num": input_data.product_num
        }
        if input_data.province_code:
            dto["province_code"] = input_data.province_code
        if input_data.city_code:
            dto["city_code"] = input_data.city_code
            
        params = {
            "method": "aliexpress.logistics.buyer.freight.calculate",
            "param_aeop_freight_calculate_for_buyer_d_t_o": str(dto) # often passed as stringified JSON
        }
        
        # Using POST for safety with complex params
        response = await client.post("/sync", params=params)
        response.raise_for_status()
        return response.json()
