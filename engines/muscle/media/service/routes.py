from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, File, Form, UploadFile, HTTPException, Depends

from engines.common.error_envelope import error_response
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context, require_tenant_membership
from engines.nexus.hardening.gate_chain import GateChain, get_gate_chain
from engines.config import runtime_config
from engines.dataset.events.schemas import DatasetEvent
from engines.logging.events.engine import run as log_event
from engines.nexus.backends import get_backend
from engines.nexus.schemas import NexusDocument, NexusKind
from engines.storage.gcs_client import GcsClient

router = APIRouter()


@router.post("/media/upload")
async def upload_media(
    file: UploadFile = File(...),
    tenant_id: str = Form(None),
    tags: Optional[str] = Form(None),
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
    gate_chain: GateChain = Depends(get_gate_chain),
):
    require_tenant_membership(auth_context, request_context.tenant_id)
    
    # Enforce GateChain
    try:
        gate_chain.run(ctx=request_context, action="media_upload", resource_kind="media_asset")
    except HTTPException as exc:
        raise exc

    tenant = request_context.tenant_id
    tag_list = [t for t in (tags.split(",") if tags else []) if t]

    try:
        content = await file.read()
    except Exception as exc:  # pragma: no cover - narrow failure
        return error_response(code="media.read_failed", message=f"failed to read upload: {exc}", status_code=400)

    try:
        gcs = GcsClient()
        asset_id = uuid.uuid4().hex
        path = f"{asset_id}/{file.filename}"
        gcs_uri = gcs.upload_raw_media(tenant, path, content)

        backend = get_backend()
        doc = NexusDocument(id=asset_id, text=gcs_uri)
        backend.write_snippet(NexusKind.data, doc, tags=["media"] + tag_list)

        event = DatasetEvent(
            tenantId=tenant,
            env=request_context.env or "dev",
            surface="media",
            agentId="media-upload",
            input={"filename": file.filename, "tags": tag_list},
            output={"gcs_uri": gcs_uri},
            metadata={"kind": "media.upload", "asset_id": asset_id},
            timestamp=datetime.now(timezone.utc),
        )
        log_event(event)

        return {"asset_id": asset_id, "gcs_uri": gcs_uri, "tags": tag_list}
    except Exception as exc:
        return error_response(code="media.upload_failed", message=str(exc), status_code=500)


@router.get("/media/stack")
def list_media(
    tenant_id: str | None = None,
    limit: int = 20,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    require_tenant_membership(auth_context, request_context.tenant_id)
    tenant = request_context.tenant_id
    try:
        backend = get_backend()
        # For now, retrieve by tags; in future use dedicated media collection.
        docs = backend.query_by_tags(NexusKind.data, tags=["media"], limit=limit)
        items = [
            {"asset_id": doc.id, "text": doc.text, "tenant_id": tenant}
            for doc in docs
        ]
        return {"items": items}
    except Exception as exc:
        return error_response(code="media.list_failed", message=str(exc), status_code=500)
