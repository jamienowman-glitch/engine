from __future__ import annotations
import httpx
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore

# --- Input Models ---

class Search1688Input(BaseModel):
    url: str = Field(..., description="Target 1688 Search or Product URL to scrape.")

# --- Connector Logic ---

async def _get_client_token(ctx: RequestContext) -> str:
    secrets = LocalSecretStore()
    api_token = secrets.get_secret(f"apify-token-{ctx.tenant_id}") or secrets.get_secret("apify-token")
    if not api_token:
        raise ValueError("Missing 'apify-token' in secrets.")
    return api_token

# --- Handlers ---

async def search_products(ctx: RequestContext, input_data: Search1688Input) -> List[Dict[str, Any]]:
    token = await _get_client_token(ctx)
    
    # Actor: ecomscrape/1688-product-details-page-scraper
    actor_id = "ecomscrape~1688-product-details-page-scraper"
    endpoint = f"https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items"
    
    params = {"token": token}
    payload = {
        "startUrls": [{"url": input_data.url}]
    }
    
    async with httpx.AsyncClient() as client:
        # Long timeout for scraping
        response = await client.post(endpoint, json=payload, params=params, timeout=60.0)
        response.raise_for_status()
        return response.json()
