from __future__ import annotations
import httpx
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore

class SendMicrosoftEmailInput(BaseModel):
    to_email: str
    subject: str
    body: str
    content_type: str = Field("Text", description="Text or HTML")

async def _get_client(ctx: RequestContext) -> httpx.AsyncClient:
    secrets = LocalSecretStore()
    api_token = secrets.get_secret(f"microsoft-token-{ctx.tenant_id}") or secrets.get_secret("microsoft-token")
    
    if not api_token:
        raise ValueError("Missing 'microsoft-token' in secrets.")

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
        
    return httpx.AsyncClient(headers=headers, base_url="https://graph.microsoft.com/v1.0")

def _build_message_payload(input_data: SendMicrosoftEmailInput):
    return {
        "subject": input_data.subject,
        "body": {
            "contentType": input_data.content_type,
            "content": input_data.body
        },
        "toRecipients": [
            {
                "emailAddress": {
                    "address": input_data.to_email
                }
            }
        ]
    }

async def send_email(ctx: RequestContext, input_data: SendMicrosoftEmailInput) -> Dict[str, Any]:
    async with await _get_client(ctx) as client:
        payload = {
            "message": _build_message_payload(input_data),
            "saveToSentItems": "true"
        }
        response = await client.post("/me/sendMail", json=payload)
        # Graph SendMail returns 202 Accepted and no content usually
        if response.status_code == 202:
            return {"status": "sent", "to": input_data.to_email}
        response.raise_for_status()
        return response.json()

async def create_draft(ctx: RequestContext, input_data: SendMicrosoftEmailInput) -> Dict[str, Any]:
    async with await _get_client(ctx) as client:
        # POST /me/messages creates a draft
        payload = _build_message_payload(input_data)
        response = await client.post("/me/messages", json=payload)
        response.raise_for_status()
        return response.json() # Returns full message object including ID
