#!/usr/bin/env python3
"""
Issues a valid dev JWT token signed with AUTH_JWT_SIGNING.
Usage: scripts/issue_dev_token.py
"""
import sys
import os
import json
import base64
import hmac
from hashlib import sha256

# Ensure AUTH_JWT_SIGNING matches dev_local_env.sh
SECRET = os.getenv("AUTH_JWT_SIGNING", "dev-jwt-secret-1234")

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

def issue_token():
    header = {"alg": "HS256", "typ": "JWT"}
    claims = {
        "sub": "dev-user-001",
        "email": "dev@local.test",
        "tenant_ids": ["t_system"],
        "default_tenant_id": "t_system",
        "role_map": {"t_system": "owner"}
    }
    
    secret_bytes = SECRET.encode("utf-8")
    signing_input = ".".join([
        _b64url(json.dumps(header, separators=(",", ":"), sort_keys=True).encode()),
        _b64url(json.dumps(claims, separators=(",", ":"), sort_keys=True).encode())
    ])
    signature = hmac.new(secret_bytes, signing_input.encode("utf-8"), sha256).digest()
    token = signing_input + "." + _b64url(signature)
    print(token)

if __name__ == "__main__":
    issue_token()
