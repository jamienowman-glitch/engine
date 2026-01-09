from __future__ import annotations

import hashlib
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from engines.common.error_envelope import error_response
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context, require_tenant_membership
from engines.registry.service import (
    AtomsPayload,
    ComponentRegistryService,
    ComponentsPayload,
    RegistrySpec,
    RegistrySpecsPayload,
    get_component_registry_service,
)

router = APIRouter(prefix="/registry", tags=["registry"])

def _require_membership(auth: AuthContext, context: RequestContext) -> None:
    try:
        require_tenant_membership(auth, context.tenant_id)
    except HTTPException as exc:
        error_response(
            code="auth.tenant_membership_required",
            message=str(exc.detail),
            status_code=exc.status_code,
            resource_kind="component_registry",
        )


def _resolve_auth_context(
    auth: AuthContext = Depends(get_auth_context),
) -> AuthContext:
    return auth


def _compute_etag(
    payload: BaseModel,
    exclude: set[str] | None = None,
) -> str:
    normalized = payload.model_dump(exclude=exclude)
    serialized = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return f"\"{digest}\""


def _respond_with_etag(
    payload: BaseModel,
    request: Request,
    exclude: set[str] | None = None,
) -> Response:
    etag = _compute_etag(payload, exclude=exclude)
    if_none_match = request.headers.get("if-none-match")
    if if_none_match:
        for token in if_none_match.split(","):
            if token.strip() == etag:
                response = Response(status_code=304)
                response.headers["ETag"] = etag
                return response
    content = payload.model_dump()
    response = JSONResponse(content=content, status_code=200)
    response.headers["ETag"] = etag
    return response


@router.get("/components", response_model=ComponentsPayload)
def get_components(
    request: Request,
    context: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(_resolve_auth_context),
    service: ComponentRegistryService = Depends(get_component_registry_service),
) -> Response:
    _require_membership(auth, context)
    payload = service.get_components(context)
    return _respond_with_etag(payload, request)


@router.get("/atoms", response_model=AtomsPayload)
def get_atoms(
    request: Request,
    context: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(_resolve_auth_context),
    service: ComponentRegistryService = Depends(get_component_registry_service),
) -> Response:
    _require_membership(auth, context)
    payload = service.get_atoms(context)
    return _respond_with_etag(payload, request)


@router.get("/specs", response_model=RegistrySpecsPayload)
def get_registry_specs(
    request: Request,
    kind: str = Query(..., regex="^(atom|component|lens|graphlens|canvas)$"),
    cursor: Optional[str] = Query(None),
    context: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(_resolve_auth_context),
    service: ComponentRegistryService = Depends(get_component_registry_service),
) -> Response:
    _require_membership(auth, context)
    payload = service.list_specs(context, kind=kind, cursor=cursor)
    etag = _compute_etag(payload, exclude={"etag"})
    payload_with_etag = payload.model_copy(update={"etag": etag})
    return _respond_with_etag(payload_with_etag, request, exclude={"etag"})


@router.get("/specs/{spec_id}", response_model=RegistrySpec)
def get_registry_spec(
    spec_id: str,
    request: Request,
    context: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(_resolve_auth_context),
    service: ComponentRegistryService = Depends(get_component_registry_service),
) -> Response:
    _require_membership(auth, context)
    spec = service.get_spec(context, spec_id)
    if not spec:
        error_response(
            code="component_registry.spec_not_found",
            message=f"Spec not found: {spec_id}",
            status_code=404,
            resource_kind="component_registry",
            details={"spec_id": spec_id},
        )
    return _respond_with_etag(spec, request)


@router.get("/graphlenses", response_model=RegistrySpecsPayload)
def get_graphlenses(
    request: Request,
    cursor: Optional[str] = Query(None),
    context: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(_resolve_auth_context),
    service: ComponentRegistryService = Depends(get_component_registry_service),
) -> Response:
    """List graphlenses (typed alias for /specs?kind=graphlens)."""
    _require_membership(auth, context)
    payload = service.list_specs(context, kind="graphlens", cursor=cursor)
    etag = _compute_etag(payload, exclude={"etag"})
    payload_with_etag = payload.model_copy(update={"etag": etag})
    return _respond_with_etag(payload_with_etag, request, exclude={"etag"})


@router.get("/canvases", response_model=RegistrySpecsPayload)
def get_canvases(
    request: Request,
    cursor: Optional[str] = Query(None),
    context: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(_resolve_auth_context),
    service: ComponentRegistryService = Depends(get_component_registry_service),
) -> Response:
    """List canvases (typed alias for /specs?kind=canvas)."""
    _require_membership(auth, context)
    payload = service.list_specs(context, kind="canvas", cursor=cursor)
    etag = _compute_etag(payload, exclude={"etag"})
    payload_with_etag = payload.model_copy(update={"etag": etag})
    return _respond_with_etag(payload_with_etag, request, exclude={"etag"})
