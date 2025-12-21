from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SignupRequest(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = None
    tenant_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[dict] = None
    tenant: Optional[dict] = None
    memberships: Optional[list[dict]] = None
