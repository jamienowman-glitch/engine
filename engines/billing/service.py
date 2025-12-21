from __future__ import annotations

import os
from typing import Optional

from engines.billing.models import CheckoutSessionRequest, CheckoutSessionResponse, SubscriptionRecord
from engines.billing.repository import InMemorySubscriptionRepository, SubscriptionRepository
from engines.common.identity import RequestContext

try:  # pragma: no cover - optional dependency
    import stripe
except Exception:  # pragma: no cover
    stripe = None


class BillingError(RuntimeError):
    pass


class BillingService:
    def __init__(self, repo: Optional[SubscriptionRepository] = None, stripe_client=None) -> None:
        self.repo = repo or InMemorySubscriptionRepository()
        self._stripe = stripe_client or stripe

    def create_checkout_session(self, ctx: RequestContext, payload: CheckoutSessionRequest) -> CheckoutSessionResponse:
        if not self._stripe:
            raise BillingError("stripe_not_installed")
        secret = os.getenv("STRIPE_SECRET_KEY")
        if not secret:
            raise BillingError("missing STRIPE_SECRET_KEY")
        self._stripe.api_key = secret
        price_id = self._resolve_price_id(payload.plan_key)
        success_url = payload.success_url or os.getenv("STRIPE_SUCCESS_URL")
        cancel_url = payload.cancel_url or os.getenv("STRIPE_CANCEL_URL")
        if not success_url or not cancel_url:
            raise BillingError("missing_success_or_cancel_url")
        metadata = {"tenant_id": ctx.tenant_id, "plan_key": payload.plan_key}
        session = self._stripe.checkout.Session.create(  # type: ignore[attr-defined]
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            line_items=[{"price": price_id, "quantity": 1}],
            metadata=metadata,
        )
        return CheckoutSessionResponse(session_id=session["id"], url=session.get("url", ""))

    def set_comped(self, tenant_id: str, plan_key: str, comped: bool = True) -> SubscriptionRecord:
        record = self.repo.get(tenant_id) or SubscriptionRecord(tenant_id=tenant_id, plan_key=plan_key)
        record.comped = comped
        record.status = "active" if comped else record.status
        return self.repo.upsert(record)

    def get_subscription(self, tenant_id: str) -> Optional[SubscriptionRecord]:
        return self.repo.get(tenant_id)

    def handle_webhook(self, signature_header: str, payload: str) -> dict:
        if not self._stripe:
            raise BillingError("stripe_not_installed")
        secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        if not secret:
            raise BillingError("missing STRIPE_WEBHOOK_SECRET")
        try:
            event = self._stripe.Webhook.construct_event(payload, signature_header, secret)  # type: ignore[attr-defined]
        except Exception as exc:
            raise BillingError(f"invalid_webhook: {exc}") from exc
        self._apply_event(event)
        return {"received": True}

    def _apply_event(self, event) -> None:
        event_type = event.get("type")
        if isinstance(event, dict):
            data = event.get("data", {}).get("object", {})
        else:
            data_obj = getattr(event, "data", None)
            data = getattr(data_obj, "object", {}) if data_obj else {}
        if not isinstance(data, dict):
            return
        metadata = data.get("metadata") or {}
        tenant_id = metadata.get("tenant_id")
        plan_key = metadata.get("plan_key") or "unknown"
        if not tenant_id:
            return
        record = self.repo.get(tenant_id) or SubscriptionRecord(tenant_id=tenant_id, plan_key=plan_key)
        if record.comped:
            record.status = "active"
            self.repo.upsert(record)
            return
        if event_type == "checkout.session.completed":
            record.status = "active"
            record.stripe_customer_id = data.get("customer")
            record.stripe_subscription_id = data.get("subscription")
        elif event_type in {"invoice.payment_failed", "customer.subscription.paused"}:
            record.status = "past_due"
        elif event_type in {"customer.subscription.deleted", "customer.subscription.canceled"}:
            record.status = "canceled"
        self.repo.upsert(record)

    @staticmethod
    def _resolve_price_id(plan_key: str) -> str:
        env_key = f"STRIPE_PRICE_{plan_key.upper()}"
        price = os.getenv(env_key) or os.getenv("STRIPE_PRICE_DEFAULT")
        if not price:
            raise BillingError(f"missing price for plan_key={plan_key}")
        return price


_default_service: Optional[BillingService] = None


def get_billing_service() -> BillingService:
    global _default_service
    if _default_service is None:
        _default_service = BillingService()
    return _default_service


def set_billing_service(service: BillingService) -> None:
    global _default_service
    _default_service = service
