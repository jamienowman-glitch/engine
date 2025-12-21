"""Minimal HS256 JWT issue/verify built on the existing key spine."""
from __future__ import annotations

import base64
import os
import hmac
import json
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Dict, List

from engines.common.keys import TenantKeySelector
from engines.common.secrets import SecretNotFound
from engines.identity.state import identity_repo

SYSTEM_TENANT = "system"
JWT_SLOT = "auth_jwt_signing"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


@dataclass
class AuthContext:
    user_id: str
    email: str
    tenant_ids: List[str]
    default_tenant_id: str
    role_map: Dict[str, str]
    provider: str = "internal"
    claims: Dict[str, Any] = field(default_factory=dict)


class JwtService:
    def __init__(self, selector: TenantKeySelector) -> None:
        self._selector = selector

    def _get_secret(self) -> str:
        try:
            material = self._selector.get_config(SYSTEM_TENANT, "prod", JWT_SLOT)
            return material.secret
        except Exception:
            env_secret = os.getenv("AUTH_JWT_SIGNING")
            if not env_secret:
                raise
            return env_secret

    def issue_token(self, claims: Dict[str, object]) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        secret = self._get_secret().encode("utf-8")
        signing_input = ".".join(
            [
                _b64url(json.dumps(header, separators=(",", ":"), sort_keys=True).encode()),
                _b64url(json.dumps(claims, separators=(",", ":"), sort_keys=True).encode()),
            ]
        )
        signature = hmac.new(secret, signing_input.encode("utf-8"), sha256).digest()
        return signing_input + "." + _b64url(signature)

    def decode_token(self, token: str) -> AuthContext:
        try:
            header_b64, payload_b64, sig_b64 = token.split(".")
        except ValueError:
            raise ValueError("invalid token")
        secret = self._get_secret().encode("utf-8")
        signing_input = header_b64 + "." + payload_b64
        expected_sig = hmac.new(secret, signing_input.encode("utf-8"), sha256).digest()
        if not hmac.compare_digest(expected_sig, _b64url_decode(sig_b64)):
            raise ValueError("invalid signature")
        payload = json.loads(_b64url_decode(payload_b64))
        return AuthContext(
            user_id=payload["sub"],
            email=payload.get("email", ""),
            tenant_ids=payload.get("tenant_ids", []),
            default_tenant_id=payload.get("default_tenant_id", ""),
            role_map=payload.get("role_map", {}),
            provider="internal",
            claims=payload,
        )


def default_jwt_service() -> JwtService:
    try:
        selector = TenantKeySelector(identity_repo)
    except Exception:
        class EnvSecretClient:
            def access_secret(self, secret_id: str) -> str:
                val = os.getenv(secret_id)
                if not val:
                    raise SecretNotFound(secret_id)
                return val

        selector = TenantKeySelector(identity_repo, secret_client=EnvSecretClient())
    return JwtService(selector)
