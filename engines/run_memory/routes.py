from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from engines.common.error_envelope import error_response
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context, require_tenant_membership
from engines.run_memory.service_reject import (
    RunMemoryServiceReject,
)
from engines.run_memory.cloud_run_memory import VersionConflictError
from engines.run_memory.service import RunMemoryService

router = APIRouter(prefix="/run_memory", tags=["run_memory"])

def _require_membership(auth: AuthContext, context: RequestContext) -> None:
    try:
        require_tenant_membership(auth, context.tenant_id)
    except HTTPException as exc:
        error_response(
            code="auth.tenant_membership_required",
            message=str(exc.detail),
            status_code=exc.status_code,
            resource_kind="run_memory",
        )


def _resolve_service(
    context: RequestContext = Depends(get_request_context),
) -> RunMemoryService | RunMemoryServiceReject:
    try:
        return RunMemoryService(context)
    except RuntimeError:
        return RunMemoryServiceReject(context)


class WritePayload(BaseModel):
    key: str
    value: Any
    run_id: str
    expected_version: Optional[int] = None


class ReadResponse(BaseModel):
    key: str
    value: Any
    version: int
    created_by: str
    created_at: str
    updated_by: str
    updated_at: str


class ListKeysResponse(BaseModel):
    keys: List[str]


@router.post("/write", response_model=ReadResponse)
def write_value(
    payload: WritePayload,
    context: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(get_auth_context),
    service: RunMemoryService | RunMemoryServiceReject = Depends(_resolve_service),
):
    """Write value to run memory."""
    _require_membership(auth, context)

    try:
        result = service.write(
            key=payload.key,
            value=payload.value,
            run_id=payload.run_id,
            expected_version=payload.expected_version,
        )
        return result
    except VersionConflictError as exc:
        error_response(
            code="run_memory.version_conflict",
            message=str(exc),
            status_code=409,
            resource_kind="run_memory",
        )
    except Exception as exc:
        error_response(
            code="run_memory.write_failed",
            message=str(exc),
            status_code=500,
            resource_kind="run_memory",
        )


@router.get("/read", response_model=ReadResponse)
def read_value(
    key: str = Query(...),
    run_id: str = Query(...),
    version: Optional[int] = Query(None),
    context: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(get_auth_context),
    service: RunMemoryService | RunMemoryServiceReject = Depends(_resolve_service),
):
    """Read value from run memory."""
    _require_membership(auth, context)

    try:
        result = service.read(key, run_id, version)
        if not result:
            error_response(
                code="run_memory.key_not_found",
                message=f"Key '{key}' not found in run {run_id}",
                status_code=404,
                resource_kind="run_memory",
            )
        return {**result, "key": key}
    except Exception as exc:
        error_response(
            code="run_memory.read_failed",
            message=str(exc),
            status_code=500,
            resource_kind="run_memory",
        )


@router.get("/keys", response_model=ListKeysResponse)
def list_keys(
    run_id: str = Query(...),
    context: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(get_auth_context),
    service: RunMemoryService | RunMemoryServiceReject = Depends(_resolve_service),
):
    """List all keys for a run."""
    _require_membership(auth, context)

    try:
        keys = service.list_keys(run_id)
        return {"keys": keys}
    except Exception as exc:
        error_response(
            code="run_memory.list_failed",
            message=str(exc),
            status_code=500,
            resource_kind="run_memory",
        )
