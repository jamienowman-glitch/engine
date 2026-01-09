from __future__ import annotations
import httpx
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore

# --- Input Models ---

class CreateMetaCampaignInput(BaseModel):
    name: str
    objective: str = Field(..., description="OUTCOME_SALES, OUTCOME_LEADS, OUTCOME_TRAFFIC, etc.")
    status: str = Field("PAUSED", description="ACTIVE, PAUSED")
    special_ad_categories: List[str] = Field(default_factory=list, description="List of categories or empty for NONE")

class CreateMetaAdSetInput(BaseModel):
    name: str
    campaign_id: str
    daily_budget: Optional[int] = Field(None, description="Daily budget in cents (e.g. 1000 = $10)")
    billing_event: str = "IMPRESSIONS"
    bid_amount: Optional[int] = None
    status: str = "PAUSED"
    targeting: Dict[str, Any] = Field(default_factory=dict, description="Geo, age, interests")

class CreateMetaAdInput(BaseModel):
    name: str
    adset_id: str
    creative_id: str = Field(..., description="ID of existing Ad Creative")
    status: str = "PAUSED"

class GetMetaInsightsInput(BaseModel):
    level: str = Field("account", description="account, campaign, adset, ad")
    date_preset: str = "maximum"
    fields: List[str] = Field(["spend", "cpm", "cpc", "ctr", "actions"], description="Metrics to fetch")

# --- Connector Logic ---

async def _get_client(ctx: RequestContext) -> tuple[httpx.AsyncClient, str]:
    secrets = LocalSecretStore()
    
    api_token = secrets.get_secret(f"meta-ads-token-{ctx.tenant_id}") or secrets.get_secret("meta-ads-token")
    ad_account_id = secrets.get_secret(f"meta-ad-account-id-{ctx.tenant_id}") or secrets.get_secret("meta-ad-account-id")
    
    if not api_token:
        raise ValueError("Missing 'meta-ads-token' in secrets.")
    if not ad_account_id:
        raise ValueError("Missing 'meta-ad-account-id' in secrets.")
        
    # Ensure ID starts with act_
    if not ad_account_id.startswith("act_"):
        ad_account_id = f"act_{ad_account_id}"

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
        
    return httpx.AsyncClient(headers=headers, base_url="https://graph.facebook.com/v19.0"), ad_account_id

# --- Handlers ---

async def create_campaign(ctx: RequestContext, input_data: CreateMetaCampaignInput) -> Dict[str, Any]:
    client, ad_account_id = await _get_client(ctx)
    async with client:
        payload = {
            "name": input_data.name,
            "objective": input_data.objective,
            "status": input_data.status,
            "special_ad_categories": input_data.special_ad_categories or []
        }
        
        response = await client.post(f"/{ad_account_id}/campaigns", json=payload)
        response.raise_for_status()
        return response.json()

async def create_ad_set(ctx: RequestContext, input_data: CreateMetaAdSetInput) -> Dict[str, Any]:
    client, ad_account_id = await _get_client(ctx)
    async with client:
        payload = {
            "name": input_data.name,
            "campaign_id": input_data.campaign_id,
            "billing_event": input_data.billing_event,
            "status": input_data.status,
            "targeting": input_data.targeting
        }
        if input_data.daily_budget:
            payload["daily_budget"] = input_data.daily_budget
        if input_data.bid_amount:
            payload["bid_amount"] = input_data.bid_amount
            
        response = await client.post(f"/{ad_account_id}/adsets", json=payload)
        response.raise_for_status()
        return response.json()

async def create_ad(ctx: RequestContext, input_data: CreateMetaAdInput) -> Dict[str, Any]:
    client, ad_account_id = await _get_client(ctx)
    async with client:
        payload = {
            "name": input_data.name,
            "adset_id": input_data.adset_id,
            "creative": {"creative_id": input_data.creative_id},
            "status": input_data.status
        }
        
        response = await client.post(f"/{ad_account_id}/ads", json=payload)
        response.raise_for_status()
        return response.json()

async def get_insights(ctx: RequestContext, input_data: GetMetaInsightsInput) -> Dict[str, Any]:
    client, ad_account_id = await _get_client(ctx)
    async with client:
        params = {
            "level": input_data.level,
            "date_preset": input_data.date_preset,
            "fields": ",".join(input_data.fields)
        }
        
        response = await client.get(f"/{ad_account_id}/insights", params=params)
        response.raise_for_status()
        return response.json()
