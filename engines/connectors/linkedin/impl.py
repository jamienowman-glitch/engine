from __future__ import annotations
import httpx
from typing import Dict, Any, Optional
from pydantic import BaseModel

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore

class ShareLinkedInUpdateInput(BaseModel):
    text: str
    url: Optional[str] = None
    visibility: str = "PUBLIC" # PUBLIC, CONNECTIONS

class GetLinkedInProfileInput(BaseModel):
    pass

async def _get_client(ctx: RequestContext) -> httpx.AsyncClient:
    secrets = LocalSecretStore()
    token = secrets.get_secret(f"linkedin-access-token-{ctx.tenant_id}") or secrets.get_secret("linkedin-access-token")
    
    if not token:
        raise ValueError("Missing 'linkedin-access-token'.")

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    return httpx.AsyncClient(headers=headers, base_url="https://api.linkedin.com/v2")

async def get_profile(ctx: RequestContext, input_data: GetLinkedInProfileInput) -> Dict[str, Any]:
    async with await _get_client(ctx) as client:
        resp = await client.get("/me")
        resp.raise_for_status()
        return resp.json()

async def share_update(ctx: RequestContext, input_data: ShareLinkedInUpdateInput) -> Dict[str, Any]:
    async with await _get_client(ctx) as client:
        # 1. Get Author URN (User ID)
        me_resp = await client.get("/me")
        me_resp.raise_for_status()
        person_id = me_resp.json()["id"]
        author_urn = f"urn:li:person:{person_id}"
        
        # 2. Construct UGC Payload
        share_content = {
            "shareCommentary": {
                "text": input_data.text
            },
            "shareMediaCategory": "NONE"
        }
        
        if input_data.url:
            share_content["shareMediaCategory"] = "ARTICLE"
            share_content["media"] = [{
                "status": "READY",
                "description": {"text": "Link"},
                "originalUrl": input_data.url
            }]
            
        payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": share_content
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": input_data.visibility
            }
        }
        
        resp = await client.post("/ugcPosts", json=payload)
        resp.raise_for_status()
        return resp.json()
