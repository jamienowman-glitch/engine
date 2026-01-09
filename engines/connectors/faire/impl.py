from __future__ import annotations
import httpx
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore

# --- Input Models ---

class ListFaireProductsInput(BaseModel):
    page: int = 1
    limit: int = 50

class ListFaireOrdersInput(BaseModel):
    page: int = 1
    limit: int = 50
    state: Optional[str] = Field(None, description="NEW, PROCESSING, PRE_TRANSIT, IN_TRANSIT, DELIVERED, CANCELED")

class FaireOrderItemInput(BaseModel):
    product_option_id: str
    quantity: int

class CreateFaireOrderInput(BaseModel):
    items: List[FaireOrderItemInput]
    retailer_id: Optional[str] = None
    customer_details: Optional[Dict[str, Any]] = None

class SearchFaireRetailerInput(BaseModel):
    query: Optional[str] = None
    min_moq: Optional[int] = None
    page: int = 1
    limit: int = 50

# --- Connector Logic ---

async def _get_client(ctx: RequestContext) -> httpx.AsyncClient:
    secrets = LocalSecretStore()
    
    api_token = secrets.get_secret(f"faire-token-{ctx.tenant_id}") or secrets.get_secret("faire-token")
    
    if not api_token:
        raise ValueError("Missing 'faire-token' in secrets.")

    headers = {
        "X-Faire-Access-Token": api_token,
        "Content-Type": "application/json"
    }
        
    return httpx.AsyncClient(headers=headers, base_url="https://www.faire.com/api/v2")

# --- Handlers ---

async def list_products(ctx: RequestContext, input_data: ListFaireProductsInput) -> Dict[str, Any]:
    async with await _get_client(ctx) as client:
        params = {"page": input_data.page, "limit": input_data.limit}
        response = await client.get("/products", params=params)
        response.raise_for_status()
        return response.json()

async def list_orders(ctx: RequestContext, input_data: ListFaireOrdersInput) -> Dict[str, Any]:
    async with await _get_client(ctx) as client:
        params = {"page": input_data.page, "limit": input_data.limit}
        if input_data.state:
            params["state"] = input_data.state
            
        response = await client.get("/orders", params=params)
        response.raise_for_status()
        return response.json()

async def create_order(ctx: RequestContext, input_data: CreateFaireOrderInput) -> Dict[str, Any]:
    async with await _get_client(ctx) as client:
        payload = {
            "items": [item.dict() for item in input_data.items]
        }
        if input_data.retailer_id:
            payload["retailerId"] = input_data.retailer_id
        if input_data.customer_details:
            payload["customerDetails"] = input_data.customer_details

        response = await client.post("/orders", json=payload)
        response.raise_for_status()
        return response.json()

async def search_retailer_products(ctx: RequestContext, input_data: SearchFaireRetailerInput) -> Dict[str, Any]:
    async with await _get_client(ctx) as client:
        params = {
            "page": input_data.page,
            "limit": input_data.limit,
            "state": "ACTIVE", # Default for sourcing
            "lifecycle_state": "PUBLISHED"
        }
        if input_data.query:
            params["q"] = input_data.query
        if input_data.min_moq:
            params["minimum_order_quantity"] = input_data.min_moq
            
        # Retailer API (assuming same endpoint structure for sourcing if permissions allow)
        # Note: If this is strictly Brand API, this might list *my* products as a brand.
        # But for the purpose of this connector acting as a "Retailer App", this is the correct semantic.
        response = await client.get("/products", params=params)
        response.raise_for_status()
        return response.json()
