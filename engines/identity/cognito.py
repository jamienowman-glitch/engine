"""AWS Cognito JWT verification (RS256, JWKS cache)."""
from __future__ import annotations

import json
import os
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional

from engines.identity.jwt_service import AuthContext

# JWKS cache keyed by URL -> {"keys": [...], "fetched_at": ts}
_jwks_cache: Dict[str, Dict[str, Any]] = {}
_verifier: Optional["CognitoJwtVerifier"] = None


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64url_decode(data + padding)


def base64url_decode(data: str) -> bytes:
    import base64

    return base64.urlsafe_b64decode(data.encode("utf-8"))


def base64url_encode(data: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


@dataclass
class CognitoConfig:
    issuer: str
    audience: Optional[str]
    jwks_url: str
    token_use: str = "id"
    cache_ttl_seconds: int = 300


class CognitoVerificationError(Exception):
    pass


def load_cognito_config() -> Optional[CognitoConfig]:
    issuer = os.getenv("COGNITO_ISSUER")
    region = os.getenv("COGNITO_REGION")
    user_pool_id = os.getenv("COGNITO_USER_POOL_ID")
    audience = os.getenv("COGNITO_APP_CLIENT_ID") or os.getenv("COGNITO_AUDIENCE")
    jwks_url = os.getenv("COGNITO_JWKS_URL")
    if not issuer and region and user_pool_id:
        issuer = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"
    if issuer and not jwks_url:
        jwks_url = issuer.rstrip("/") + "/.well-known/jwks.json"
    if not issuer or not jwks_url:
        return None
    token_use = os.getenv("COGNITO_TOKEN_USE", "id")
    return CognitoConfig(issuer=issuer.rstrip("/"), audience=audience, jwks_url=jwks_url, token_use=token_use)


def _fetch_jwks(jwks_url: str, ttl_seconds: int = 300) -> Dict[str, Any]:
    if jwks_url in _jwks_cache:
        entry = _jwks_cache[jwks_url]
        fetched_at = entry.get("fetched_at", 0)
        ttl = entry.get("cache_ttl", ttl_seconds)
        if time.time() - fetched_at < ttl:
            return entry["jwks"]
    with urllib.request.urlopen(jwks_url, timeout=5) as resp:  # nosec B310 - runtime-configured URL
        body = resp.read()
        jwks = json.loads(body.decode("utf-8"))
        _jwks_cache[jwks_url] = {"jwks": jwks, "fetched_at": time.time(), "cache_ttl": ttl_seconds}
        return jwks


def _rsa_verify_rs256(signing_input: bytes, signature: bytes, n: int, e: int) -> bool:
    """Verify an RS256 signature using PKCS#1 v1.5 (pure Python)."""
    # Decode signature to integer and apply modexp with public exponent
    key_len = (n.bit_length() + 7) // 8
    sig_int = int.from_bytes(signature, "big")
    m_int = pow(sig_int, e, n)
    em = m_int.to_bytes(key_len, "big")

    # EMSA-PKCS1-v1_5 encoding for SHA-256
    import hashlib

    digest = hashlib.sha256(signing_input).digest()
    digest_info = bytes.fromhex("3031300d060960864801650304020105000420") + digest
    if len(em) < len(digest_info) + 11:
        return False
    if not (em[0] == 0x00 and em[1] == 0x01):
        return False
    # Expect 0xFF padding until a 0x00 separator
    try:
        sep_idx = em.index(b"\x00", 2)
    except ValueError:
        return False
    padding = em[2:sep_idx]
    if any(b != 0xFF for b in padding):
        return False
    return em[sep_idx + 1 :] == digest_info


class CognitoJwtVerifier:
    def __init__(self, config: CognitoConfig) -> None:
        self.config = config

    def verify(self, token: str) -> AuthContext:
        header_b64, payload_b64, sig_b64 = self._split_token(token)
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        header = json.loads(_b64url_decode(header_b64))
        payload = json.loads(_b64url_decode(payload_b64))
        sig = _b64url_decode(sig_b64)

        if header.get("alg") != "RS256":
            raise CognitoVerificationError("unsupported alg")

        kid = header.get("kid")
        key = self._select_key(kid)
        if not key:
            raise CognitoVerificationError("jwks_key_not_found")
        n_b64 = key.get("n")
        e_b64 = key.get("e")
        if not n_b64 or not e_b64:
            raise CognitoVerificationError("jwks_key_invalid")
        n = int.from_bytes(_b64url_decode(n_b64), "big")
        e = int.from_bytes(_b64url_decode(e_b64), "big")
        if not _rsa_verify_rs256(signing_input, sig, n, e):
            raise CognitoVerificationError("invalid_signature")

        self._validate_claims(payload)

        email = payload.get("email") or payload.get("cognito:username") or ""
        user_id = payload.get("sub") or payload.get("username")
        if not user_id:
            raise CognitoVerificationError("missing_sub")

        return AuthContext(
            user_id=str(user_id),
            email=str(email),
            tenant_ids=[],
            default_tenant_id="",
            role_map={},
            provider="cognito",
            claims=payload,
        )

    # --- internal helpers ---
    def _select_key(self, kid: Optional[str]) -> Optional[Dict[str, Any]]:
        jwks = _fetch_jwks(self.config.jwks_url, ttl_seconds=self.config.cache_ttl_seconds)
        for k in jwks.get("keys", []):
            if kid is None or k.get("kid") == kid:
                return k
        return None

    def _validate_claims(self, payload: Dict[str, Any]) -> None:
        iss = payload.get("iss", "").rstrip("/")
        if iss != self.config.issuer.rstrip("/"):
            raise CognitoVerificationError("invalid_issuer")
        aud = payload.get("aud")
        if self.config.audience:
            if isinstance(aud, list):
                if self.config.audience not in aud:
                    raise CognitoVerificationError("invalid_audience")
            elif aud != self.config.audience:
                raise CognitoVerificationError("invalid_audience")
        token_use = payload.get("token_use")
        if self.config.token_use and token_use != self.config.token_use:
            raise CognitoVerificationError("invalid_token_use")
        now = int(time.time())
        if "exp" in payload:
            if now >= int(payload["exp"]):
                raise CognitoVerificationError("token_expired")
        if "nbf" in payload and now < int(payload["nbf"]):
            raise CognitoVerificationError("token_not_yet_valid")

    @staticmethod
    def _split_token(token: str) -> tuple[str, str, str]:
        parts = token.split(".")
        if len(parts) != 3:
            raise CognitoVerificationError("invalid_token")
        return parts[0], parts[1], parts[2]


def get_cognito_verifier() -> Optional[CognitoJwtVerifier]:
    global _verifier
    if _verifier:
        return _verifier
    cfg = load_cognito_config()
    if not cfg:
        return None
    _verifier = CognitoJwtVerifier(cfg)
    return _verifier


def clear_jwks_cache() -> None:
    _jwks_cache.clear()


def reset_cognito_verifier() -> None:
    """Testing helper to clear cached verifier and JWKS."""
    global _verifier
    _verifier = None
    clear_jwks_cache()
