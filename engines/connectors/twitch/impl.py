from __future__ import annotations
import httpx
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore

class CreateTwitchClipInput(BaseModel):
    broadcaster_id: Optional[str] = None # Optional, defaults to self
    has_delay: bool = False

class UpdateTwitchStreamInfoInput(BaseModel):
    broadcaster_id: Optional[str] = None
    title: Optional[str] = None
    game_id: Optional[str] = None
    tags: Optional[List[str]] = None

async def _get_client(ctx: RequestContext) -> httpx.AsyncClient:
    secrets = LocalSecretStore()
    token = secrets.get_secret(f"twitch-access-token-{ctx.tenant_id}") or secrets.get_secret("twitch-access-token")
    client_id = secrets.get_secret(f"twitch-client-id-{ctx.tenant_id}") or secrets.get_secret("twitch-client-id")
    
    if not token or not client_id:
        raise ValueError("Missing Twitch credentials (token or client-id).")

    headers = {
        "Authorization": f"Bearer {token}",
        "Client-Id": client_id
    }
    return httpx.AsyncClient(headers=headers, base_url="https://api.twitch.tv/helix")

async def _resolve_broadcaster_id(client: httpx.AsyncClient, input_id: Optional[str]) -> str:
    if input_id:
        return input_id
    # Fetch Me
    resp = await client.get("/users")
    resp.raise_for_status()
    data = resp.json()["data"]
    if not data:
        raise ValueError("Could not resolve Twitch User ID.")
    return data[0]["id"]

async def create_clip(ctx: RequestContext, input_data: CreateTwitchClipInput) -> Dict[str, Any]:
    async with await _get_client(ctx) as client:
        bid = await _resolve_broadcaster_id(client, input_data.broadcaster_id)
        
        payload = {"broadcaster_id": bid, "has_delay": input_data.has_delay}
        resp = await client.post("/clips", params=payload) # Helix uses query params for POST clips!
        resp.raise_for_status()
        return resp.json()

async def update_stream_info(ctx: RequestContext, input_data: UpdateTwitchStreamInfoInput) -> Dict[str, Any]:
    async with await _get_client(ctx) as client:
        bid = await _resolve_broadcaster_id(client, input_data.broadcaster_id)
        
        payload = {}
        if input_data.title:
            payload["title"] = input_data.title
        if input_data.game_id:
            payload["game_id"] = input_data.game_id
        if input_data.tags:
            payload["tags"] = input_data.tags
            
        resp = await client.patch("/channels", params={"broadcaster_id": bid}, json=payload)
        resp.raise_for_status()
        return {"status": "updated"}
