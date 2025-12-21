from __future__ import annotations

import math
import os
import random
import time
from typing import Dict

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from engines.identity import cognito
from engines.identity.auth import get_auth_context, require_tenant_membership
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.state import set_identity_repo


def setup_function(_fn):
    set_identity_repo(InMemoryIdentityRepository())
    cognito.reset_cognito_verifier()


def _is_probable_prime(n: int, rounds: int = 6) -> bool:
    if n in (2, 3):
        return True
    if n % 2 == 0 or n < 2:
        return False
    # Miller-Rabin
    s, d = 0, n - 1
    while d % 2 == 0:
        d //= 2
        s += 1
    for _ in range(rounds):
        a = random.randrange(2, n - 1)
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for __ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def _generate_prime(bits: int) -> int:
    while True:
        candidate = random.getrandbits(bits) | 1 | (1 << bits - 1)
        if _is_probable_prime(candidate):
            return candidate


def _generate_rsa_key(bits: int = 512) -> tuple[int, int, int]:
    e = 65537
    while True:
        p = _generate_prime(bits // 2)
        q = _generate_prime(bits // 2)
        phi = (p - 1) * (q - 1)
        if math.gcd(e, phi) == 1:
            n = p * q
            d = pow(e, -1, phi)
            return n, e, d


def _b64url(data: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _rs256_sign(signing_input: bytes, n: int, d: int) -> bytes:
    import hashlib

    digest = hashlib.sha256(signing_input).digest()
    digest_info = bytes.fromhex("3031300d060960864801650304020105000420") + digest
    k = (n.bit_length() + 7) // 8
    padding_len = k - len(digest_info) - 3
    em = b"\x00\x01" + b"\xff" * padding_len + b"\x00" + digest_info
    m_int = int.from_bytes(em, "big")
    sig_int = pow(m_int, d, n)
    return sig_int.to_bytes(k, "big")


def _make_token(n: int, d: int, claims: Dict[str, object], kid: str = "test") -> str:
    import json

    header = {"alg": "RS256", "kid": kid, "typ": "JWT"}
    payload = claims
    signing_input = ".".join([_b64url(json.dumps(header, separators=(",", ":"), sort_keys=True).encode()), _b64url(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())])
    signature = _rs256_sign(signing_input.encode("utf-8"), n, d)
    return signing_input + "." + _b64url(signature)


def _jwks_from_key(n: int, e: int, kid: str = "test") -> Dict[str, object]:
    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": kid,
                "alg": "RS256",
                "n": _b64url(n.to_bytes((n.bit_length() + 7) // 8, "big")),
                "e": _b64url(e.to_bytes((e.bit_length() + 7) // 8, "big")),
                "use": "sig",
            }
        ]
    }


def test_cognito_bootstrap_and_membership(monkeypatch):
    repo = InMemoryIdentityRepository()
    set_identity_repo(repo)
    jwks_url = "https://example.com/mock-jwks.json"
    issuer = "https://example.com/cognito"
    audience = "client-123"

    n, e, d = _generate_rsa_key()
    jwks = _jwks_from_key(n, e)
    monkeypatch.setenv("COGNITO_ISSUER", issuer)
    monkeypatch.setenv("COGNITO_APP_CLIENT_ID", audience)
    monkeypatch.setenv("COGNITO_JWKS_URL", jwks_url)
    monkeypatch.setattr(cognito, "_fetch_jwks", lambda _url, ttl_seconds=300: jwks)
    cognito.reset_cognito_verifier()

    now = int(time.time())
    token = _make_token(
        n,
        d,
        {
            "sub": "cog-user-1",
            "email": "cog@example.com",
            "aud": audience,
            "iss": issuer,
            "token_use": "id",
            "exp": now + 3600,
        },
    )

    app = FastAPI()

    @app.get("/auth/me")
    def me(auth=Depends(get_auth_context)):
        return auth

    @app.get("/protected")
    def protected(auth=Depends(get_auth_context)):
        require_tenant_membership(auth, auth.default_tenant_id)
        return {"ok": True, "tenant_id": auth.default_tenant_id}

    client = TestClient(app)

    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "cog@example.com"
    assert body["tenant_ids"]
    assert body["role_map"][body["default_tenant_id"]] == "owner"

    # Idempotent bootstrap (tenant/membership reused)
    resp2 = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    body2 = resp2.json()
    assert body2["default_tenant_id"] == body["default_tenant_id"]
    memberships = repo.list_memberships_for_user(body2["user_id"])
    assert len(memberships) == 1

    resp3 = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert resp3.status_code == 200
    assert resp3.json()["tenant_id"] == body["default_tenant_id"]
