from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SubscriptionRecord(BaseModel):
    tenant_id: str
    plan_key: str
    status: Literal["active", "past_due", "canceled", "incomplete"] = "incomplete"
    comped: bool = False
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    updated_at: datetime = Field(default_factory=_now)
    created_at: datetime = Field(default_factory=_now)


class CheckoutSessionRequest(BaseModel):
    plan_key: str
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutSessionResponse(BaseModel):
    session_id: str
    url: str
