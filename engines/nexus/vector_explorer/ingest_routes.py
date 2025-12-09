"""HTTP ingest endpoint for Haze vector explorer."""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from engines.nexus.vector_explorer.ingest_service import IngestError, VectorIngestService

router = APIRouter()
_service: VectorIngestService | None = None


def _get_service() -> VectorIngestService:
    global _service
    if _service is None:
        _service = VectorIngestService()
    return _service


@router.post("/vector-explorer/ingest")
async def ingest_vector_item(
    tenant_id: str = Form(..., pattern=r"^t_[a-z0-9_-]+$"),
    env: str = Form(...),
    space: str = Form(...),
    content_type: str = Form(...),
    label: str = Form(...),
    tags: Optional[str] = Form(None),
    text_content: Optional[str] = Form(None),
    source_ref: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
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
            tenant_id=tenant_id,
            env=env,
            space=space,
            content_type=content_type,
            label=label,
            tags=[t for t in (tags.split(",") if tags else []) if t],
            text_content=text_content,
            file_bytes=file_bytes,
            filename=file.filename if file else None,
            source_ref=source_ref_dict,
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
