from __future__ import annotations
import httpx
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore

# --- Input Models ---

class AssetInput(BaseModel):
    url: str
    printArea: str = "default"

class ItemInput(BaseModel):
    sku: str
    copies: int = 1
    assets: List[AssetInput]

class RecipientInput(BaseModel):
    name: str
    address1: str
    city: str
    country_code: str
    zip: str
    email: str

class GetQuoteInput(BaseModel):
    destinationCountryCode: str
    currencyCode: str = "USD"
    items: List[Dict[str, Any]] = Field(..., description="List of items (sku, copies)")

class CreateProdigiOrderInput(BaseModel):
    shippingMethod: str = "Budget"
    recipient: RecipientInput
    items: List[ItemInput]
    idempotencyKey: Optional[str] = None

class GetProdigiOrderInput(BaseModel):
    orderId: str

# --- Connector Logic ---

async def _get_client(ctx: RequestContext) -> httpx.AsyncClient:
    secrets = LocalSecretStore()
    
    # Check Tenant Specific ID first
    api_key = secrets.get_secret(f"prodigi-api-key-{ctx.tenant_id}") or secrets.get_secret("prodigi-api-key")
    
    if not api_key:
        raise ValueError("Missing 'prodigi-api-key' in secrets.")

    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
        
    return httpx.AsyncClient(headers=headers, base_url="https://api.prodigi.com/v4.0")

# --- Handlers ---

async def get_quote(ctx: RequestContext, input_data: GetQuoteInput) -> Dict[str, Any]:
    payload = {
        "destinationCountryCode": input_data.destinationCountryCode,
        "currencyCode": input_data.currencyCode,
        "items": input_data.items
    }
    async with await _get_client(ctx) as client:
        # Quote is POST /quotes
        response = await client.post("/quotes", json=payload)
        response.raise_for_status()
        return response.json()

async def create_order(ctx: RequestContext, input_data: CreateProdigiOrderInput) -> Dict[str, Any]:
    # Need to convert Pydantic models to dict manually or use model_dump if v2
    # Simple recursive dict conversion
    payload = {
        "shippingMethod": input_data.shippingMethod,
        "recipient": input_data.recipient.dict(),
        "items": [item.dict() for item in input_data.items]
    }
    
    if input_data.idempotencyKey:
        payload["idempotencyKey"] = input_data.idempotencyKey

    async with await _get_client(ctx) as client:
        response = await client.post("/orders", json=payload)
        response.raise_for_status()
        return response.json()

async def get_order(ctx: RequestContext, input_data: GetProdigiOrderInput) -> Dict[str, Any]:
    async with await _get_client(ctx) as client:
        response = await client.get(f"/orders/{input_data.orderId}")
        response.raise_for_status()
        return response.json()
