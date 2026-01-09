from __future__ import annotations
import httpx
import base64
from email.mime.text import MIMEText
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore

class ListGmailThreadsInput(BaseModel):
    max_results: int = 10
    query: str = "label:INBOX is:unread"

class SendGmailInput(BaseModel):
    to_email: str
    subject: str
    body: str

async def _get_client(ctx: RequestContext) -> httpx.AsyncClient:
    secrets = LocalSecretStore()
    api_token = secrets.get_secret(f"gmail-token-{ctx.tenant_id}") or secrets.get_secret("gmail-token")
    
    if not api_token:
        raise ValueError("Missing 'gmail-token' in secrets.")

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
        
    return httpx.AsyncClient(headers=headers, base_url="https://gmail.googleapis.com")

def _create_message_raw(input_data: SendGmailInput) -> str:
    message = MIMEText(input_data.body)
    message['to'] = input_data.to_email
    message['subject'] = input_data.subject
    raw = base64.urlsafe_b64encode(message.as_bytes())
    return raw.decode()

async def list_threads(ctx: RequestContext, input_data: ListGmailThreadsInput) -> Dict[str, Any]:
    async with await _get_client(ctx) as client:
        params = {"maxResults": input_data.max_results, "q": input_data.query}
        response = await client.get("/gmail/v1/users/me/threads", params=params)
        response.raise_for_status()
        return response.json()

async def send_email(ctx: RequestContext, input_data: SendGmailInput) -> Dict[str, Any]:
    async with await _get_client(ctx) as client:
        payload = {
            "raw": _create_message_raw(input_data)
        }
        response = await client.post("/gmail/v1/users/me/messages/send", json=payload)
        response.raise_for_status()
        return response.json()

async def create_draft(ctx: RequestContext, input_data: SendGmailInput) -> Dict[str, Any]:
    async with await _get_client(ctx) as client:
        payload = {
            "message": {
                "raw": _create_message_raw(input_data)
            }
        }
        response = await client.post("/gmail/v1/users/me/drafts", json=payload)
        response.raise_for_status()
        return response.json()
