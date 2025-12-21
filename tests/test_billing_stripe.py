from __future__ import annotations

import hashlib
import hmac
import json
import time
from types import SimpleNamespace

from engines.billing.models import CheckoutSessionRequest
from engines.billing.service import BillingService, BillingError
from engines.billing.repository import InMemorySubscriptionRepository
from engines.common.identity import RequestContext


class _FakeStripe:
    def __init__(self, secret: str):
        self.api_key = None
        self._secret = secret
        self._created = {}
        self.checkout = SimpleNamespace(Session=SimpleNamespace(create=self._create))
        self.Webhook = SimpleNamespace(construct_event=self._construct_event)

    def _create(self, **kwargs):
        self._created.update(kwargs)
        return {"id": "cs_test", "url": "https://stripe.test/checkout"}

    def _construct_event(self, payload, sig_header, secret):
        # Minimal signature check (HMAC SHA256)
        timestamp, sig = self._parse(sig_header)
        expected = self._sign(payload, timestamp, secret)
        if not hmac.compare_digest(expected, sig):
            raise ValueError("invalid signature")
        return json.loads(payload)

    @staticmethod
    def _parse(header: str):
        parts = header.split(",")
        t_part = next(p for p in parts if p.startswith("t="))
        s_part = next(p for p in parts if p.startswith("v1="))
        return int(t_part.split("=")[1]), s_part.split("=")[1]

    @staticmethod
    def _sign(payload: str, timestamp: int, secret: str) -> str:
        signed = f"{timestamp}.{payload}"
        return hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()


def _stripe_signature(secret: str, payload: str, timestamp: int) -> str:
    signed_payload = f"{timestamp}.{payload}"
    sig = hmac.new(secret.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={sig}"


def test_checkout_session_uses_price(monkeypatch):
    repo = InMemorySubscriptionRepository()
    fake_stripe = _FakeStripe("sk_test_dummy")
    svc = BillingService(repo=repo, stripe_client=fake_stripe)
    ctx = RequestContext(tenant_id="t_demo", env="dev")

    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setenv("STRIPE_PRICE_PRO", "price_123")

    res = svc.create_checkout_session(ctx, CheckoutSessionRequest(plan_key="pro", success_url="https://s/success", cancel_url="https://s/cancel"))
    assert res.session_id == "cs_test"
    assert fake_stripe._created["line_items"][0]["price"] == "price_123"
    assert fake_stripe._created["metadata"]["tenant_id"] == "t_demo"


def test_webhook_signature_and_state(monkeypatch):
    repo = InMemorySubscriptionRepository()
    secret = "whsec_test"
    fake_stripe = _FakeStripe(secret)
    svc = BillingService(repo=repo, stripe_client=fake_stripe)
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)

    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"tenant_id": "t_demo", "plan_key": "pro"},
                "customer": "cus_123",
                "subscription": "sub_123",
            }
        },
    }
    payload = json.dumps(event)
    timestamp = int(time.time())
    sig_header = _stripe_signature(secret, payload, timestamp)

    result = svc.handle_webhook(sig_header, payload)
    assert result["received"] is True
    record = repo.get("t_demo")
    assert record is not None
    assert record.status == "active"
    assert record.plan_key == "pro"


def test_webhook_rejects_missing_secret(monkeypatch):
    repo = InMemorySubscriptionRepository()
    fake_stripe = _FakeStripe("secret")
    svc = BillingService(repo=repo, stripe_client=fake_stripe)
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    try:
        svc.handle_webhook("sig", "{}")
        assert False, "expected failure"
    except BillingError:
        assert True
