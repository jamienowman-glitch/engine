"""FastAPI routes exposing CAD viewer endpoints."""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from engines.common.identity import RequestContext, get_request_context
from engines.cad_viewer.service import get_cad_viewer_service, MissingArtifactError
from engines.cad_viewer.models import CadGanttView, CadOverlayView

router = APIRouter(prefix="/cad/viewer", tags=["cad_viewer"])


@router.get("/{project_id}/gantt", response_model=CadGanttView)
def get_gantt(project_id: str, cost_model_id: str, context: RequestContext = Depends(get_request_context)) -> CadGanttView:
    """Return CadGanttView for a project and cost model id."""
    svc = get_cad_viewer_service()
    try:
        view = svc.build_gantt_view(project_id=project_id, cost_model_id=cost_model_id, context=context.model_dump())
        # Echo request context in meta
        view.meta["request_context"] = {
            "tenant_id": context.tenant_id,
            "env": context.env,
            "request_id": context.request_id,
        }
        return view
    except MissingArtifactError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build gantt view: {e}")


@router.get("/{project_id}/overlays", response_model=CadOverlayView)
def get_overlays(project_id: str, cost_model_id: str, context: RequestContext = Depends(get_request_context)) -> CadOverlayView:
    """Return CadOverlayView for a project and cost model id."""
    svc = get_cad_viewer_service()
    try:
        view = svc.build_overlay_view(project_id=project_id, cost_model_id=cost_model_id, context=context.model_dump())
        view.meta["request_context"] = {
            "tenant_id": context.tenant_id,
            "env": context.env,
            "request_id": context.request_id,
        }
        return view
    except MissingArtifactError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build overlay view: {e}")
