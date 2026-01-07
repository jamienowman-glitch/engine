"""Canonical error envelope for all Engines responses.

Standardized structure:
{
  "error": {
    "code": "string",
    "message": "string",
    "http_status": 400,
    "gate": "firearms | strategy_lock | budget | kill_switch | null",
    "action_name": "string | null",
    "resource_kind": "string | null",
    "details": {}
  }
}
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Literal
from fastapi import HTTPException
from pydantic import BaseModel, Field


GateType = Literal["firearms", "strategy_lock", "budget", "kill_switch", "temperature", "kpi", None]


class ErrorDetail(BaseModel):
    """Canonical error detail structure."""
    code: str
    message: str
    http_status: int
    gate: Optional[GateType] = None
    action_name: Optional[str] = None
    resource_kind: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    """Top-level error envelope returned by all Engines endpoints."""
    error: ErrorDetail


def build_error_envelope(
    code: str,
    message: str,
    status_code: int = 400,
    gate: Optional[GateType] = None,
    action_name: Optional[str] = None,
    resource_kind: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> ErrorEnvelope:
    """Construct an ErrorEnvelope (without raising).
    
    Args mirror error_response; http_status mirrors status_code.
    """
    error_detail = ErrorDetail(
        code=code,
        message=message,
        http_status=status_code,
        gate=gate,
        action_name=action_name,
        resource_kind=resource_kind,
        details=details or {},
    )
    return ErrorEnvelope(error=error_detail)


def error_response(
    code: str,
    message: str,
    status_code: int = 400,
    gate: Optional[GateType] = None,
    action_name: Optional[str] = None,
    resource_kind: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> HTTPException:
    """Construct and raise a standardized error response.
    
    Args:
        code: Machine-readable error code (e.g., "budget_threshold_exceeded")
        message: Human-readable error message
        status_code: HTTP status code (default 400)
        gate: Gate that blocked (firearms|strategy_lock|budget|kill_switch)
        action_name: The action being attempted
        resource_kind: The resource type (canvas, thread, etc.)
        details: Additional context dict
    
    Returns:
        HTTPException with canonical error envelope body
    """
    envelope = build_error_envelope(
        code=code,
        message=message,
        status_code=status_code,
        gate=gate,
        action_name=action_name,
        resource_kind=resource_kind,
        details=details,
    )
    raise HTTPException(status_code=status_code, detail=envelope.model_dump())


def missing_route_error(
    resource_kind: str,
    tenant_id: str,
    env: str,
    status_code: int = 503,
) -> HTTPException:
    """Missing routing configuration error."""
    return error_response(
        code=f"{resource_kind}.missing_route",
        message=f"No routing configured for {resource_kind}",
        status_code=status_code,
        resource_kind=resource_kind,
        details={
            "resource_kind": resource_kind,
            "tenant_id": tenant_id,
            "env": env,
        },
    )


def cursor_invalid_error(
    cursor: str,
    domain: str = "event_spine",
    resource_kind: Optional[str] = None,
) -> HTTPException:
    """Invalid or expired event cursor (410 Gone)."""
    return error_response(
        code=f"{domain}.cursor_invalid",
        message=f"Cursor invalid or expired: {cursor}",
        status_code=410,
        resource_kind=resource_kind,
        details={"cursor": cursor},
    )
