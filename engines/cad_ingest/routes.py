"""
CAD Ingest Routes - FastAPI endpoints for CAD file ingestion.

Provides:
- POST /cad/ingest: Upload and ingest CAD file
- GET /cad/model/{model_id}: Retrieve ingested model
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile

from engines.common.identity import (
    RequestContext,
    assert_context_matches,
    get_request_context,
)
from engines.identity.auth import AuthContext, get_auth_context
from engines.cad_ingest.models import (
    CadIngestRequest,
    CadIngestResponse,
    UnitKind,
)
from engines.cad_ingest.service import get_cad_ingest_service

router = APIRouter(prefix="/cad", tags=["cad_ingest"])


@router.post("/ingest", response_model=CadIngestResponse)
async def ingest_cad_file(
    file: UploadFile | None = File(None),
    source_uri: str | None = Form(None),
    format_hint: str | None = Form(None),
    unit_hint: str | None = Form(None),
    tolerance: float | None = Form(None),
    snap_to_grid: bool | None = Form(None),
    grid_size: float | None = Form(None),
    tenant_id: str | None = Form(None),
    env: str | None = Form(None),
    payload: CadIngestRequest | None = Body(None),
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    """
    Ingest a CAD file (DXF or IFC-lite).
    
    Returns CadIngestResponse with artifact ID and model metadata.
    
    Parameters (form or JSON body):
    - file: Multipart file upload
    - source_uri: Original source URI
    - format_hint: 'dxf' or 'ifc-lite' (auto-detected if omitted)
    - unit_hint: Unit system (mm|cm|m|ft|in)
    - tolerance: Healing tolerance (default 0.001)
    - snap_to_grid: Enable grid snapping
    - grid_size: Grid size for snapping
    - tenant_id: Optional, must match header if provided
    - env: Optional, must match header if provided
    """
    service = get_cad_ingest_service()
    
    try:
        if file:
            # Multipart upload
            assert_context_matches(request_context, tenant_id, env)
            content = await file.read()
            request_obj = CadIngestRequest(
                file_uri=source_uri or file.filename or "uploaded_file",
                source_uri=source_uri,
                format_hint=format_hint,
                unit_hint=UnitKind(unit_hint) if unit_hint else None,
                tolerance=tolerance or 0.001,
                snap_to_grid=snap_to_grid or False,
                grid_size=grid_size or 0.001,
                tenant_id=request_context.tenant_id,
                env=request_context.env,
                user_id=auth_context.user_id or request_context.user_id,
            )
        elif payload:
            # JSON body
            assert_context_matches(request_context, payload.tenant_id, payload.env)
            request_obj = payload
            request_obj.tenant_id = request_context.tenant_id
            request_obj.env = request_context.env
            request_obj.user_id = auth_context.user_id or request_context.user_id or payload.user_id
            
            if not request_obj.source_uri:
                raise ValueError("source_uri required for JSON body")
            
            content = None
            if request_obj.file_uri:
                # Try to read from file_uri (local path or S3)
                # For now, fail with helpful error
                raise ValueError("file_uri not supported for JSON body; use multipart upload")
        else:
            raise HTTPException(
                status_code=400,
                detail="Provide either multipart upload (file) or JSON payload",
            )
        
        if not content and not request_obj.source_uri:
            raise HTTPException(
                status_code=400,
                detail="Provide either file content or source_uri",
            )
        
        # Ingest the file
        if content:
            model, response = service.ingest(content, request_obj)
            
            # Register artifact
            artifact_id = service.register_artifact(model, request_obj)
            response.cad_model_artifact_id = artifact_id
            
            return response
        else:
            raise HTTPException(
                status_code=501,
                detail="Remote source_uri ingest not yet implemented",
            )
    
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingest failed: {exc}")
