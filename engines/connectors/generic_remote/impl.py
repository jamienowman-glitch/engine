from __future__ import annotations
from typing import Dict, Any, Optional
from pydantic import BaseModel

from engines.common.identity import RequestContext
from engines.workbench.local_secrets import LocalSecretStore

# Retrieve secrets/config
_secrets_store = None

def _get_secrets():
    global _secrets_store
    if _secrets_store is None:
        _secrets_store = LocalSecretStore()
    return _secrets_store

class RemoteCallPayload(BaseModel):
    tool: str
    arguments: Dict[str, Any]

async def proxy_call(ctx: RequestContext, payload: RemoteCallPayload) -> Dict[str, Any]:
    """
    Proxies a tool call to a remote MCP server.
    
    Config is resolved from the Tenant's secret store using the key:
    `connector.remote.{payload.tool}` or a generic gateway config.
    
    For W-02 POC, we assume a specific secret key format for the remote host:
    `conn-generic-remote-url`
    `conn-generic-remote-token`
    """
    
    # 1. Resolve Config
    _secrets = _get_secrets()
    
    base_url = _secrets.get_secret(f"conn-generic-remote-url-{ctx.tenant_id}")
    token = _secrets.get_secret(f"conn-generic-remote-token-{ctx.tenant_id}")
    
    if not base_url:
        # Fallback for dev/lab mode if not strictly tenant scoped in local secret store
        base_url = _secrets.get_secret("conn-generic-remote-url")
        token = _secrets.get_secret("conn-generic-remote-token")
        
    if not base_url:
        raise ValueError("Remote MCP URL not configured for tenant.")

    # 2. Forward Request
    # We use httpx for async IO
    import httpx
    
    headers = {
        "Content-Type": "application/json",
        "X-Tenant-ID": ctx.tenant_id,
        "X-User-ID": ctx.user_id
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    # JSON-RPC 2.0 style or REST? 
    # Spec says "Proxies JSON-RPC (or REST adapter events)".
    # We'll assume the remote side exposes a POST /tools/call endpoint compatible with us, 
    # OR a standard JSON-RPC endpoint.
    # Let's assume Northstar-to-Northstar protocol for W-02 (POST /tools/call).
    
    target_url = f"{base_url.rstrip('/')}/tools/call"
    
    # We map our payload to the remote's expected payload.
    # If remote is another Northstar Engine, it expects { tool_id, scope_name, arguments }.
    # Our Payload has `tool` (which is likely tool_id.scope or just tool_id).
    
    # Let's parse `payload.tool` -> `tool_id`, `scope_name`
    # User types "google.search", we split? 
    # Or we pass it as is.
    
    # Heuristic: split on last dot
    if "." in payload.tool:
        tool_id, scope_name = payload.tool.rsplit(".", 1)
    else:
        tool_id = payload.tool
        scope_name = "default"
        
    remote_body = {
        "tool_id": tool_id,
        "scope_name": scope_name,
        "arguments": payload.arguments
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(target_url, json=remote_body, headers=headers)
        
    if resp.status_code >= 400:
        raise RuntimeError(f"Remote Generic Proxy failed: {resp.status_code} - {resp.text}")
        
    return resp.json()
