"""HTTP ingest endpoint for Haze vector explorer."""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from engines.nexus.vector_explorer.ingest_service import IngestError, VectorIngestService
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import get_auth_context, require_tenant_membership
from engines.strategy_lock.models import ACTION_VECTOR_INGEST
from engines.strategy_lock.service import get_strategy_lock_service

router = APIRouter()
_service: VectorIngestService | None = None


def _get_service() -> VectorIngestService:
    global _service
    if _service is None:
        _service = VectorIngestService()
    return _service


@router.post("/vector-explorer/ingest")
async def ingest_vector_item(
    space: str = Form(...),
    content_type: str = Form(...),
    label: str = Form(...),
    tags: Optional[str] = Form(None),
    text_content: Optional[str] = Form(None),
    source_ref: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    get_strategy_lock_service().require_strategy_lock_or_raise(context, surface=space, action=ACTION_VECTOR_INGEST)
    try:
        file_bytes = await file.read() if file else None
    except Exception as exc:  # pragma: no cover - narrow IO failure
        raise HTTPException(status_code=400, detail=f"failed to read upload: {exc}")

    try:
        source_ref_dict = json.loads(source_ref) if source_ref else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="source_ref must be valid JSON")

    try:
        result = _get_service().ingest(
            tenant_id=context.tenant_id,
            env=context.env,
            space=space,
            content_type=content_type,
            label=label,
            tags=[t for t in (tags.split(",") if tags else []) if t],
            text_content=text_content,
            file_bytes=file_bytes,
            filename=file.filename if file else None,
            user_id=context.user_id,
            source_ref=source_ref_dict,
            context=context,
        )
    except IngestError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {
        "asset_id": result.item.id,
        "gcs_uri": result.gcs_uri,
        "corpus_space": space,
        "vector_ref": result.item.vector_ref,
    }
