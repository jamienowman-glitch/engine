from __future__ import annotations
import httpx
import asyncio
import json
import base64
import time
import hmac
import hashlib
import urllib.parse
from uuid import uuid4
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore

class PostTweetInput(BaseModel):
    text: str
    media_ids: List[str] = [] # If user already uploaded
    media_urls: List[str] = [] # Download and upload automatically
    reply_to_tweet_id: Optional[str] = None
    quote_tweet_id: Optional[str] = None

class ReplyTweetInput(BaseModel):
    tweet_id: str
    text: str
    media_urls: List[str] = []

# Minimal OAuth 1.0a Signer for httpx (to avoid deps issues)
class OAuth1Auth(httpx.Auth):
    def __init__(self, client_key, client_secret, resource_owner_key, resource_owner_secret):
        self.client_key = client_key
        self.client_secret = client_secret
        self.resource_owner_key = resource_owner_key
        self.resource_owner_secret = resource_owner_secret

    def auth_flow(self, request):
        # Add Authorization header
        # 1. Collect params
        params = {
            "oauth_consumer_key": self.client_key,
            "oauth_nonce": str(uuid4()).replace("-", ""),
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": self.resource_owner_key,
            "oauth_version": "1.0",
        }
        
        # 2. Add query params? (X usually ignores query params for body signature if form-urlencoded, but for JSON body, signature uses ONLY query/oauth params)
        # For V2 Post (JSON), body is NOT included in signature base string.
        
        # 3. Create Signature Base String
        # Method & URL
        method = request.method.upper()
        url = str(request.url).split("?")[0]
        
        # Merge params
        base_params = params.copy()
        # Parse query params from URL
        query = urllib.parse.urlparse(str(request.url)).query
        if query:
            for k, v in urllib.parse.parse_qsl(query):
                base_params[k] = v
        
        # Sort and Encode
        encoded_params = []
        for k in sorted(base_params.keys()):
            encoded_params.append(f"{urllib.parse.quote(str(k), safe='')}={urllib.parse.quote(str(base_params[k]), safe='')}")
        param_string = "&".join(encoded_params)
        
        base_string = f"{method}&{urllib.parse.quote(url, safe='')}&{urllib.parse.quote(param_string, safe='')}"
        
        # 4. Sign
        signing_key = f"{urllib.parse.quote(self.client_secret, safe='')}&{urllib.parse.quote(self.resource_owner_secret, safe='')}"
        hashed = hmac.new(signing_key.encode("utf-8"), base_string.encode("utf-8"), hashlib.sha1)
        signature = base64.b64encode(hashed.digest()).decode("utf-8")
        
        # 5. Header
        params["oauth_signature"] = signature
        # Sort for neatness
        header_parts = []
        for k in sorted(params.keys()):
             header_parts.append(f'{k}="{urllib.parse.quote(params[k], safe="")}"')
        
        auth_header = f"OAuth {', '.join(header_parts)}"
        yield request.headers.update({"Authorization": auth_header})

async def _get_client(ctx: RequestContext) -> httpx.AsyncClient:
    secrets = LocalSecretStore()
    ck = secrets.get_secret(f"twitter-consumer-key-{ctx.tenant_id}") or secrets.get_secret("twitter-consumer-key")
    cs = secrets.get_secret(f"twitter-consumer-secret-{ctx.tenant_id}") or secrets.get_secret("twitter-consumer-secret")
    at = secrets.get_secret(f"twitter-access-token-{ctx.tenant_id}") or secrets.get_secret("twitter-access-token")
    ats = secrets.get_secret(f"twitter-access-secret-{ctx.tenant_id}") or secrets.get_secret("twitter-access-secret")
    
    if not all([ck, cs, at, ats]):
        raise ValueError("Missing Twitter OAuth1 credentials.")

    auth = OAuth1Auth(ck, cs, at, ats)
    return httpx.AsyncClient(auth=auth)

async def _upload_media(client: httpx.AsyncClient, video_url: str) -> str:
    # 1. Download
    async with httpx.AsyncClient() as dl:
        r = await dl.get(video_url)
        content = r.content
        total_bytes = len(content)
        media_type = r.headers.get("content-type", "image/jpeg")

    # 2. INIT
    upload_url = "https://upload.twitter.com/1.1/media/upload.json"
    init_data = {
        "command": "INIT",
        "total_bytes": total_bytes,
        "media_type": media_type
    }
    # Note: upload endpoints usually form-encoded.
    r_init = await client.post(upload_url, data=init_data)
    r_init.raise_for_status()
    media_id = r_init.json()["media_id_string"]
    
    # 3. APPEND (Simple single chunk for now)
    # httpx multipart file upload
    files = {"media": content}
    r_append = await client.post(upload_url, data={"command": "APPEND", "media_id": media_id, "segment_index": 0}, files=files)
    if r_append.status_code < 200 or r_append.status_code > 299:
         # sometimes appends return nothing but status
         pass

    # 4. FINALIZE
    r_fin = await client.post(upload_url, data={"command": "FINALIZE", "media_id": media_id})
    r_fin.raise_for_status()
    
    # Wait if processing
    info = r_fin.json()
    if info.get("processing_info"):
        state = info["processing_info"]["state"]
        while state in ["pending", "in_progress"]:
            await asyncio.sleep(int(info["processing_info"].get("check_after_secs", 1)))
            r_stat = await client.get(upload_url, params={"command": "STATUS", "media_id": media_id})
            info = r_stat.json()
            state = info["processing_info"]["state"]
            if state == "failed":
                raise ValueError(f"Media upload failed: {info}")
    
    return media_id

async def post_tweet(ctx: RequestContext, input_data: PostTweetInput) -> Dict[str, Any]:
    async with await _get_client(ctx) as client:
        # Handle Media
        media_ids = input_data.media_ids or []
        for url in input_data.media_urls:
            mid = await _upload_media(client, url)
            media_ids.append(mid)
            
        payload = {"text": input_data.text}
        if media_ids:
            payload["media"] = {"media_ids": media_ids}
        if input_data.reply_to_tweet_id:
             payload["reply"] = {"in_reply_to_tweet_id": input_data.reply_to_tweet_id}
        if input_data.quote_tweet_id:
             payload["quote_tweet_id"] = input_data.quote_tweet_id
             
        resp = await client.post("https://api.twitter.com/2/tweets", json=payload)
        resp.raise_for_status()
        return resp.json()

async def reply_tweet(ctx: RequestContext, input_data: ReplyTweetInput) -> Dict[str, Any]:
    # Wrapper for post_tweet with reply logic
    async with await _get_client(ctx) as client:
        # Check media
        media_ids = []
        for url in input_data.media_urls:
            mid = await _upload_media(client, url)
            media_ids.append(mid)
            
        payload = {
            "text": input_data.text,
            "reply": {"in_reply_to_tweet_id": input_data.tweet_id}
        }
        if media_ids:
            payload["media"] = {"media_ids": media_ids}
            
        resp = await client.post("https://api.twitter.com/2/tweets", json=payload)
        resp.raise_for_status()
        return resp.json()
