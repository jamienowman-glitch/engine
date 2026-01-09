from __future__ import annotations
import httpx
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore

# --- Input Models ---

class RunGA4ReportInput(BaseModel):
    date_ranges: List[Dict[str, str]] = Field(..., description="[{startDate: '2023-01-01', endDate: 'today'}]")
    dimensions: List[Dict[str, str]] = Field(default_factory=list, description="[{name: 'city'}]")
    metrics: List[Dict[str, str]] = Field(..., description="[{name: 'activeUsers'}]")

# --- Connector Logic ---

async def _get_client(ctx: RequestContext) -> tuple[httpx.AsyncClient, str]:
    secrets = LocalSecretStore()
    
    # We expect a valid Access Token (Bearer)
    api_token = secrets.get_secret(f"ga4-token-{ctx.tenant_id}") or secrets.get_secret("ga4-token")
    property_id = secrets.get_secret(f"ga4-property-id-{ctx.tenant_id}") or secrets.get_secret("ga4-property-id")
    
    if not api_token:
        # Fallback: In a real prod scenario, we might exchange SA JSON for a token here.
        # For now, we standardized on Bearer tokens.
        raise ValueError("Missing 'ga4-token' (Bearer) in secrets.")
    if not property_id:
        raise ValueError("Missing 'ga4-property-id' in secrets.")

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
        
    return httpx.AsyncClient(headers=headers, base_url="https://analyticsdata.googleapis.com/v1beta"), property_id

# --- Handlers ---

async def run_report(ctx: RequestContext, input_data: RunGA4ReportInput) -> Dict[str, Any]:
    client, property_id = await _get_client(ctx)
    async with client:
        payload = {
            "dateRanges": input_data.date_ranges,
            "dimensions": input_data.dimensions,
            "metrics": input_data.metrics
        }
        
        # Endpoint: POST /properties/{propertyId}:runReport
        response = await client.post(f"/properties/{property_id}:runReport", json=payload)
        response.raise_for_status()
        return response.json()
