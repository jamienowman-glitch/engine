from __future__ import annotations

import os

from fastapi.testclient import TestClient

from engines.analytics_events.service import set_analytics_events_service, AnalyticsEventsService
from engines.chat.service.server import create_app
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.state import set_identity_repo
from engines.identity.models import Tenant, User, TenantMembership, TenantKeyConfig
from engines.identity.key_service import KeyConfigService
from engines.identity.routes_keys import set_key_service
from engines.common.keys import TenantKeySelector
from engines.identity.jwt_service import JwtService
from engines.dataset.events.schemas import DatasetEvent


class CaptureLogger:
    def __init__(self):
        self.events: list[DatasetEvent] = []

    def __call__(self, event: DatasetEvent):
        self.events.append(event)
        return {"status": "ok"}


def _setup():
    repo = InMemoryIdentityRepository()
    set_identity_repo(repo)
    os.environ["APP_ENV"] = "dev"
    os.environ["AUTH_JWT_SIGNING"] = "secret"
    repo.set_key_config(
        TenantKeyConfig(
            tenant_id="system",
            env="prod",
            slot="auth_jwt_signing",
            provider="system",
            secret_name="AUTH_JWT_SIGNING",
        )
    )
    set_key_service(KeyConfigService(repo=repo))
    tenant = Tenant(id="t_demo", name="Demo")
    user = User(email="analytics@example.com")
    repo.create_tenant(tenant)
    repo.create_user(user)
    repo.create_membership(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    selector = TenantKeySelector(repo)
    jwt = JwtService(selector)
    token = jwt.issue_token(
        {
            "sub": user.id,
            "email": user.email,
            "tenant_ids": [tenant.id],
            "default_tenant_id": tenant.id,
            "role_map": {tenant.id: "owner"},
        }
    )
    headers = {"X-Tenant-Id": tenant.id, "X-Env": "dev", "Authorization": f"Bearer {token}"}
    return tenant, headers


def test_pageview_event_records_dataset_event():
    tenant, headers = _setup()
    capture = CaptureLogger()
    set_analytics_events_service(AnalyticsEventsService(logger=capture))
    client = TestClient(create_app())
    payload = {"surface": "squared", "page_type": "home", "url": "https://example.com", "utm_source": "news"}
    resp = client.post("/analytics/events/pageview", json=payload, headers=headers)
    assert resp.status_code == 200
    assert capture.events
    evt = capture.events[0]
    assert evt.tenantId == tenant.id
    assert evt.analytics_event_type == "pageview"
    assert evt.utm_source == "news"


def test_cta_click_records_event():
    tenant, headers = _setup()
    capture = CaptureLogger()
    set_analytics_events_service(AnalyticsEventsService(logger=capture))
    client = TestClient(create_app())
    payload = {"surface": "squared", "page_type": "home", "cta_id": "cta123", "label": "Buy"}
    resp = client.post("/analytics/events/cta-click", json=payload, headers=headers)
    assert resp.status_code == 200
    evt = capture.events[0]
    assert evt.analytics_event_type == "cta_click"
    assert evt.input["cta_id"] == "cta123"
