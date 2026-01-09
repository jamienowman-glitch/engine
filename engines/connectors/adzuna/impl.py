from __future__ import annotations
import httpx
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore

class SearchAdzunaJobsInput(BaseModel):
    country: str = Field("gb", description="Country code (gb, us, etc.)")
    what: str = Field(..., description="Keywords (e.g. 'Python Developer')")
    where: Optional[str] = Field(None, description="Location (e.g. 'London')")
    results_per_page: int = 10

class GetAdzunaSalaryStatsInput(BaseModel):
    country: str = "gb"
    what: str
    where: Optional[str] = None

async def _get_client(ctx: RequestContext) -> tuple[httpx.AsyncClient, Dict[str, str]]:
    secrets = LocalSecretStore()
    app_id = secrets.get_secret(f"adzuna-app-id-{ctx.tenant_id}") or secrets.get_secret("adzuna-app-id")
    app_key = secrets.get_secret(f"adzuna-app-key-{ctx.tenant_id}") or secrets.get_secret("adzuna-app-key")
    
    if not app_id or not app_key:
        raise ValueError("Missing 'adzuna-app-id' or 'adzuna-app-key'.")

    # Adzuna uses query params for auth
    auth_params = {
        "app_id": app_id,
        "app_key": app_key
    }
    return httpx.AsyncClient(base_url="https://api.adzuna.com/v1/api"), auth_params

async def search_jobs(ctx: RequestContext, input_data: SearchAdzunaJobsInput) -> Dict[str, Any]:
    client, auth_params = await _get_client(ctx)
    async with client:
        params = auth_params.copy()
        params.update({
            "what": input_data.what,
            "results_per_page": str(input_data.results_per_page),
            "content-type": "application/json"
        })
        if input_data.where:
            params["where"] = input_data.where
            
        # Search page 1 by default
        resp = await client.get(f"/jobs/{input_data.country}/search/1", params=params)
        resp.raise_for_status()
        return resp.json()

async def get_salary_stats(ctx: RequestContext, input_data: GetAdzunaSalaryStatsInput) -> Dict[str, Any]:
    client, auth_params = await _get_client(ctx)
    async with client:
        params = auth_params.copy()
        params.update({
            "what": input_data.what,
            "content-type": "application/json"
        })
        if input_data.where:
            params["where"] = input_data.where
            
        resp = await client.get(f"/jobs/{input_data.country}/histogram", params=params)
        resp.raise_for_status()
        return resp.json()
