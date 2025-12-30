"""HMAC-signed ticket issuance/validation for Gate3 transports."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from typing import Any, Dict, Optional

from engines.common.identity import RequestContext, VALID_MODES

TICKET_TTL_SECONDS = 300


class TicketError(ValueError):
    """Raised when ticket issuance or validation fails."""


def _get_secret() -> bytes:
    secret = os.getenv("ENGINES_TICKET_SECRET")
    if not secret:
        raise TicketError("ENGINES_TICKET_SECRET is required to issue or validate tickets")
    return secret.encode("utf-8")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _unb64(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(payload: bytes, secret: bytes) -> str:
    digest = hmac.new(secret, payload, hashlib.sha256).digest()
    return _b64(digest)


def issue_ticket(scope: Dict[str, Any], expires_in: int = TICKET_TTL_SECONDS) -> str:
    """
    Issue a short-lived ticket for SSE/WS transports.
    Scope must include tenant_id, mode, and project_id (mode in VALID_MODES).
    """
    tenant_id = scope.get("tenant_id")
    mode = scope.get("mode")
    project_id = scope.get("project_id")
    if not tenant_id or not mode or not project_id:
        raise TicketError("tenant_id, mode, and project_id are required for ticket issuance")
    if mode not in VALID_MODES:
        raise TicketError(f"mode must be one of {VALID_MODES}")

    now = int(time.time())
    payload = {
        "tenant_id": tenant_id,
        "mode": mode,
        "project_id": project_id,
        "surface_id": scope.get("surface_id"),
        "app_id": scope.get("app_id"),
        "user_id": scope.get("user_id"),
        "request_id": scope.get("request_id") or str(uuid.uuid4()),
        "exp": now + expires_in,
        "iat": now,
    }
    secret = _get_secret()
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sig = _sign(body, secret)
    token = f"{_b64(body)}.{sig}"
    return token


def validate_ticket(token: str) -> Dict[str, Any]:
    """
    Validate and decode a ticket, raising TicketError if invalid or expired.
    """
    if not token or "." not in token:
        raise TicketError("invalid ticket format")
    payload_b64, sig = token.split(".", 1)
    body = _unb64(payload_b64)
    expected_sig = _sign(body, _get_secret())
    if not hmac.compare_digest(sig, expected_sig):
        raise TicketError("invalid ticket signature")
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        raise TicketError("invalid ticket payload")

    exp = payload.get("exp")
    if not exp or not isinstance(exp, int):
        raise TicketError("ticket expiry missing")
    if int(time.time()) > exp:
        raise TicketError("ticket expired")

    if payload.get("mode") not in VALID_MODES:
        raise TicketError(f"ticket mode must be one of {VALID_MODES}")
    if not payload.get("tenant_id") or not payload.get("project_id"):
        raise TicketError("ticket missing required scope fields")
    return payload


def context_from_ticket(token: str) -> RequestContext:
    payload = validate_ticket(token)
    return RequestContext(
        tenant_id=payload["tenant_id"],
        mode=payload["mode"],
        project_id=payload["project_id"],
        request_id=payload.get("request_id") or str(uuid.uuid4()),
        surface_id=payload.get("surface_id"),
        app_id=payload.get("app_id"),
        user_id=payload.get("user_id"),
        actor_id=payload.get("user_id"),
    )
