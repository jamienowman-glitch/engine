from __future__ import annotations
import httpx
import json
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore

class UploadYouTubeVideoInput(BaseModel):
    video_url: str = Field(..., description="URL of the video file to upload")
    title: str
    description: str
    tags: List[str] = []
    category_id: str = "22" # People & Blogs default
    privacy_status: str = "private" # private, public, unlisted
    is_short: bool = False # Hint to verify vertical/duration? (optional logic)

class SetYouTubeThumbnailInput(BaseModel):
    video_id: str
    image_url: str

class CreateYouTubePlaylistInput(BaseModel):
    title: str
    description: str
    privacy_status: str = "private"

class GetYouTubeAnalyticsInput(BaseModel):
    start_date: str # YYYY-MM-DD
    end_date: str
    metrics: str = "views,likes,comments,averageViewDuration"
    dimensions: str = "day"
    filters: Optional[str] = None # e.g. video==VIDEO_ID

async def _get_client(ctx: RequestContext, service: str = "data") -> httpx.AsyncClient:
    secrets = LocalSecretStore()
    api_token = secrets.get_secret(f"youtube-oauth-token-{ctx.tenant_id}") or secrets.get_secret("youtube-oauth-token")
    
    if not api_token:
        raise ValueError("Missing 'youtube-oauth-token' in secrets.")

    headers = {
        "Authorization": f"Bearer {api_token}"
    }

    base_url = "https://www.googleapis.com/youtube/v3"
    if service == "upload":
        base_url = "https://www.googleapis.com/upload/youtube/v3"
    elif service == "analytics":
        base_url = "https://youtubeanalytics.googleapis.com/v2"
        
    return httpx.AsyncClient(headers=headers, base_url=base_url)

async def upload_video(ctx: RequestContext, input_data: UploadYouTubeVideoInput) -> Dict[str, Any]:
    # 1. Download Video Content
    async with httpx.AsyncClient() as downloader:
        vid_resp = await downloader.get(input_data.video_url)
        vid_resp.raise_for_status()
        video_bytes = vid_resp.content

    # 2. Metadata
    metadata = {
        "snippet": {
            "title": input_data.title,
            "description": input_data.description,
            "tags": input_data.tags,
            "categoryId": input_data.category_id
        },
        "status": {
            "privacyStatus": input_data.privacy_status
        }
    }
    
    # 3. Upload
    async with await _get_client(ctx, service="upload") as client:
        # Multipart upload: 'part' parameter must be set
        params = {"part": "snippet,status"}
        files = {
            "body": ("metadata.json", json.dumps(metadata), "application/json"),
            "media": ("video.mp4", video_bytes, "application/octet-stream")
        }
        
        response = await client.post("/videos", params=params, files=files)
        response.raise_for_status()
        return response.json()

async def set_thumbnail(ctx: RequestContext, input_data: SetYouTubeThumbnailInput) -> Dict[str, Any]:
    async with httpx.AsyncClient() as downloader:
        img_resp = await downloader.get(input_data.image_url)
        img_resp.raise_for_status()
        img_bytes = img_resp.content

    async with await _get_client(ctx, service="upload") as client:
        # thumbnails/set endpoint on Upload API
        params = {"videoId": input_data.video_id}
        files = {"media": ("thumb.jpg", img_bytes, "application/octet-stream")}
        
        response = await client.post("/thumbnails/set", params=params, files=files)
        response.raise_for_status()
        return response.json()

async def create_playlist(ctx: RequestContext, input_data: CreateYouTubePlaylistInput) -> Dict[str, Any]:
    async with await _get_client(ctx, service="data") as client:
        payload = {
            "snippet": {
                "title": input_data.title,
                "description": input_data.description
            },
            "status": {
                "privacyStatus": input_data.privacy_status
            }
        }
        params = {"part": "snippet,status"}
        response = await client.post("/playlists", params=params, json=payload)
        response.raise_for_status()
        return response.json()

async def get_analytics(ctx: RequestContext, input_data: GetYouTubeAnalyticsInput) -> Dict[str, Any]:
    async with await _get_client(ctx, service="analytics") as client:
        params = {
            "ids": "channel==MINE",
            "startDate": input_data.start_date,
            "endDate": input_data.end_date,
            "metrics": input_data.metrics,
            "dimensions": input_data.dimensions
        }
        if input_data.filters:
            params["filters"] = input_data.filters
            
        response = await client.get("/reports", params=params)
        response.raise_for_status()
        return response.json()
