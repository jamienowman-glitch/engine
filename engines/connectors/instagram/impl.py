from __future__ import annotations
import httpx
import asyncio
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore

class PublishInstagramMediaInput(BaseModel):
    media_url: str
    media_type: str = Field(..., description="IMAGE, VIDEO, REELS, STORIES")
    caption: str = ""
    cover_url: Optional[str] = None # For Reels

class GetInstagramInsightsInput(BaseModel):
    media_id: Optional[str] = None
    metric: str = "impressions,reach"

async def _get_client(ctx: RequestContext) -> tuple[httpx.AsyncClient, str]:
    secrets = LocalSecretStore()
    api_token = secrets.get_secret(f"instagram-access-token-{ctx.tenant_id}") or secrets.get_secret("instagram-access-token")
    account_id = secrets.get_secret(f"instagram-business-id-{ctx.tenant_id}") or secrets.get_secret("instagram-business-id")
    
    if not api_token or not account_id:
        raise ValueError("Missing Instagram credentials in secrets.")

    headers = {
        "Authorization": f"Bearer {api_token}"
    }
        
    return httpx.AsyncClient(headers=headers, base_url="https://graph.facebook.com/v19.0"), account_id

async def publish_media(ctx: RequestContext, input_data: PublishInstagramMediaInput) -> Dict[str, Any]:
    client, account_id = await _get_client(ctx)
    async with client:
        # 1. Create Container
        payload = {
            "caption": input_data.caption
        }
        
        if input_data.media_type == "IMAGE":
            payload["image_url"] = input_data.media_url
        elif input_data.media_type in ["VIDEO", "REELS"]:
            payload["media_type"] = "REELS" # Graph API V19 prefers REELS usually or VIDEO
            payload["video_url"] = input_data.media_url
            if input_data.cover_url:
                payload["cover_url"] = input_data.cover_url
        elif input_data.media_type == "STORIES":
            payload["media_type"] = "STORIES"
            # stories can be image or video
            if ".mp4" in input_data.media_url:
                 payload["video_url"] = input_data.media_url
            else:
                 payload["image_url"] = input_data.media_url

        create_resp = await client.post(f"/{account_id}/media", params=payload)
        create_resp.raise_for_status()
        container_id = create_resp.json()["id"]
        
        # 2. If Video, Wait for Processing
        if input_data.media_type in ["VIDEO", "REELS", "STORIES"] and "video_url" in payload:
            for _ in range(10): # polling limit
                status_resp = await client.get(f"/{container_id}", params={"fields": "status_code"})
                status = status_resp.json().get("status_code")
                if status == "FINISHED":
                    break
                if status == "ERROR":
                    raise ValueError("Instagram Video Processing Failed")
                await asyncio.sleep(2) # wait
        
        # 3. Publish Container
        publish_payload = {"creation_id": container_id}
        pub_resp = await client.post(f"/{account_id}/media_publish", params=publish_payload)
        pub_resp.raise_for_status()
        
        return pub_resp.json()

async def get_insights(ctx: RequestContext, input_data: GetInstagramInsightsInput) -> Dict[str, Any]:
    client, account_id = await _get_client(ctx)
    async with client:
        # User or Media insights
        target_id = input_data.media_id if input_data.media_id else account_id
        period = "day" if not input_data.media_id else None # User insights need period
        
        params = {"metric": input_data.metric}
        if period:
             params["period"] = period
             
        resp = await client.get(f"/{target_id}/insights", params=params)
        resp.raise_for_status()
        return resp.json()
