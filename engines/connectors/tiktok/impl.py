from __future__ import annotations
import httpx
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore

class PostTikTokVideoInput(BaseModel):
    video_url: str
    title: str = Field(..., description="Caption")
    privacy_level: str = "SELF_ONLY" # PUBLIC_TO_EVERYONE, MUTUAL_FOLLOW_FRIENDS, SELF_ONLY
    disable_duet: bool = False
    disable_stitch: bool = False
    disable_comment: bool = False

class GetTikTokAnalyticsInput(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    fields: Optional[List[str]] = None

async def _get_client(ctx: RequestContext) -> httpx.AsyncClient:
    secrets = LocalSecretStore()
    api_token = secrets.get_secret(f"tiktok-access-token-{ctx.tenant_id}") or secrets.get_secret("tiktok-access-token")
    
    if not api_token:
        raise ValueError("Missing 'tiktok-access-token' in secrets.")

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
        
    return httpx.AsyncClient(headers=headers, base_url="https://open.tiktokapis.com")

async def post_video(ctx: RequestContext, input_data: PostTikTokVideoInput) -> Dict[str, Any]:
    # 1. Download Video
    async with httpx.AsyncClient() as downloader:
        vid_resp = await downloader.get(input_data.video_url)
        vid_resp.raise_for_status()
        video_bytes = vid_resp.content
        video_size = len(video_bytes)

    async with await _get_client(ctx) as client:
        # 2. Init
        init_payload = {
            "post_info": {
                "title": input_data.title,
                "privacy_level": input_data.privacy_level,
                "disable_duet": input_data.disable_duet,
                "disable_stitch": input_data.disable_stitch,
                "disable_comment": input_data.disable_comment,
                "video_cover_timestamp_ms": 1000
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": video_size, # Uploading in one chunk for simplicity
                "total_chunk_count": 1
            },
            "post_mode": "DIRECT_POST",
            "media_type": "VIDEO"
        }
        
        init_resp = await client.post("/v2/post/publish/content/init/", json=init_payload)
        init_resp.raise_for_status()
        init_data = init_resp.json()
        
        upload_url = init_data["data"]["upload_url"]
        publish_id = init_data["data"]["publish_id"]
        
        # 3. Upload to the provided URL (PUT)
        # Note: Depending on response, headers might be needed (Content-Range etc). 
        # Standard TikTok Direct Post Upload usually just expects the bytes.
        headers = {"Content-Type": "video/mp4", "Content-Length": str(video_size)}
        # Must use a fresh client for the upload URL as it doesn't need Bearer usually (signature is in URL)
        async with httpx.AsyncClient() as uploader:
            upload_resp = await uploader.put(upload_url, content=video_bytes, headers=headers)
            upload_resp.raise_for_status()
            
        return {"status": "published", "publish_id": publish_id}

async def get_analytics(ctx: RequestContext, input_data: GetTikTokAnalyticsInput) -> Dict[str, Any]:
    # Not implementing full analytics as endpoint varies by scope (Display API vs Research).
    # Placeholder for structure.
    return {"status": "not_implemented_in_mvp"}
