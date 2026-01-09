from __future__ import annotations
import httpx
import asyncio
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore

# --- Input Models ---

class ListProductsInput(BaseModel):
    limit: int = Field(10, description="Number of products to return")
    search: Optional[str] = Field(None, description="Search term")

class ListOrdersInput(BaseModel):
    limit: int = Field(10, description="Number of orders to return")
    status: Optional[str] = Field(None, description="Filter by status (draft, pending, etc)")

class CreateOrderInput(BaseModel):
    recipient_name: str
    recipient_email: str
    recipient_address1: str
    recipient_city: str
    recipient_country_code: str
    recipient_zip: str
    items: List[Dict[str, Any]] = Field(..., description="List of items (variant_id, quantity, etc)")

class GetStoreInput(BaseModel):
    pass

class CreateProductInput(BaseModel):
    name: str = Field(..., description="Name of the product")
    thumbnail: Optional[str] = Field(None, description="URL of thumbnail image")

class AddVariantInput(BaseModel):
    sync_product_id: int = Field(..., description="The ID of the Sync Product")
    retail_price: float = Field(..., description="Retail price for this variant")
    variant_id: int = Field(..., description="Catalog Variant ID (e.g. 4011 for Gildan 64000 L Black)")
    files: List[Dict[str, Any]] = Field(..., description="Print files. List of {url: ..., type: 'default', ...}")

class UpdateVariantInput(BaseModel):
    variant_id: int = Field(..., description="Sync Variant ID (NOT catalog ID)")
    retail_price: Optional[float] = Field(None, description="New retail price")
    name: Optional[str] = None

class GenerateMockupsInput(BaseModel):
    variant_ids: List[int] = Field(..., description="List of Catalog Variant IDs")
    format: str = Field("jpg", description="jpg or png")
    files: List[Dict[str, Any]] = Field(..., description="Print files. {placement: 'default', image_url: ...}")

class GetCatalogItemInput(BaseModel):
    id: int = Field(..., description="Catalog Product ID (e.g. 71 for Gildan 64000)")

# --- Connector Logic ---

async def _get_client(ctx: RequestContext) -> httpx.AsyncClient:
    secrets = LocalSecretStore()
    
    # Check Tenant Specific ID first
    api_key = secrets.get_secret(f"printful-api-key-{ctx.tenant_id}") or secrets.get_secret("printful-api-key")
    store_id = secrets.get_secret(f"printful-store-id-{ctx.tenant_id}") or secrets.get_secret("printful-store-id")
    
    if not api_key:
        raise ValueError("Missing 'printful-api-key' in secrets.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    if store_id:
        headers["X-PF-Store-Id"] = store_id
        
    return httpx.AsyncClient(headers=headers, base_url="https://api.printful.com")

# --- Handlers ---

async def get_store_info(ctx: RequestContext, input_data: GetStoreInput) -> Dict[str, Any]:
    async with await _get_client(ctx) as client:
        response = await client.get("/stores")
        response.raise_for_status()
        return response.json()

async def list_products(ctx: RequestContext, input_data: ListProductsInput) -> Dict[str, Any]:
    params = {"limit": input_data.limit}
    if input_data.search:
        params["search"] = input_data.search
        
    async with await _get_client(ctx) as client:
        response = await client.get("/store/products", params=params)
        response.raise_for_status()
        return response.json()

async def list_orders(ctx: RequestContext, input_data: ListOrdersInput) -> Dict[str, Any]:
    params = {"limit": input_data.limit}
    if input_data.status:
        params["status"] = input_data.status
        
    async with await _get_client(ctx) as client:
        response = await client.get("/orders", params=params)
        response.raise_for_status()
        return response.json()

async def create_order(ctx: RequestContext, input_data: CreateOrderInput) -> Dict[str, Any]:
    payload = {
        "recipient": {
            "name": input_data.recipient_name,
            "email": input_data.recipient_email,
            "address1": input_data.recipient_address1,
            "city": input_data.recipient_city,
            "country_code": input_data.recipient_country_code,
            "zip": input_data.recipient_zip
        },
        "items": input_data.items
    }
    async with await _get_client(ctx) as client:
        response = await client.post("/orders", json=payload)
        response.raise_for_status()
        return response.json()

# --- Advanced Handlers ---

async def create_product(ctx: RequestContext, input_data: CreateProductInput) -> Dict[str, Any]:
    payload = {
        "sync_product": {
            "name": input_data.name,
            "thumbnail": input_data.thumbnail
        }
    }
    async with await _get_client(ctx) as client:
        response = await client.post("/store/products", json=payload)
        response.raise_for_status()
        return response.json()

async def add_variant(ctx: RequestContext, input_data: AddVariantInput) -> Dict[str, Any]:
    payload = {
        "sync_product_id": input_data.sync_product_id,
        "sync_variant": {
            "retail_price": input_data.retail_price,
            "variant_id": input_data.variant_id,
            "files": input_data.files
        }
    }
    # Note: Endpoint is /store/products/{id}/variants using POST
    async with await _get_client(ctx) as client:
        response = await client.post(f"/store/products/{input_data.sync_product_id}/variants", json=payload)
        response.raise_for_status()
        return response.json()

async def update_variant(ctx: RequestContext, input_data: UpdateVariantInput) -> Dict[str, Any]:
    payload = {
        "sync_variant": {}
    }
    if input_data.retail_price is not None:
        payload["sync_variant"]["retail_price"] = input_data.retail_price
    if input_data.name:
        payload["sync_variant"]["name"] = input_data.name

    async with await _get_client(ctx) as client:
        # Endpoint: PUT /store/variants/{id}
        response = await client.put(f"/store/variants/{input_data.variant_id}", json=payload)
        response.raise_for_status()
        return response.json()

async def get_catalog_item(ctx: RequestContext, input_data: GetCatalogItemInput) -> Dict[str, Any]:
    async with await _get_client(ctx) as client:
        response = await client.get(f"/products/{input_data.id}")
        response.raise_for_status()
        return response.json()

async def generate_mockups(ctx: RequestContext, input_data: GenerateMockupsInput) -> Dict[str, Any]:
    """
    Polls the Mockup Generator API until images are ready.
    """
    payload = {
        "variant_ids": input_data.variant_ids,
        "format": input_data.format,
        "files": input_data.files
    }
    
    async with await _get_client(ctx) as client:
        # 1. Create Task
        response = await client.post("/mockup-generator/create_task", json=payload)
        response.raise_for_status()
        task_data = response.json()
        task_key = task_data.get("result", {}).get("task_key")
        
        if not task_key:
            return {"error": "Failed to start mockup task", "raw": task_data}
        
        # 2. Poll for Status (Max 10 attempts, 2s interval = 20s wait)
        for _ in range(10):
            await asyncio.sleep(2.0)
            status_res = await client.get(f"/mockup-generator/task?task_key={task_key}")
            status_res.raise_for_status()
            status_data = status_res.json()
            
            status = status_data.get("result", {}).get("status")
            if status == "completed":
                return status_data # Contains mockups list
            elif status == "failed":
                return {"error": "Mockup generation failed", "detail": status_data}
        
        return {"error": "Timed out waiting for mockups", "task_key": task_key}
