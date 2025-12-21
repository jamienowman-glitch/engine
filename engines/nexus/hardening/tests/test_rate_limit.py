import pytest
from fastapi import HTTPException

from engines.common.identity import RequestContext
from engines.nexus.hardening.rate_limit import InMemoryRateLimitStorage, RateLimitService


def _build_context(tenant_id: str):
    return RequestContext(tenant_id=tenant_id, env="dev")


def test_throttle_survives_restart():
    storage = InMemoryRateLimitStorage()
    svc1 = RateLimitService(storage=storage)
    ctx = _build_context("t_a")
    svc1.check_rate_limit(ctx, action="act", limit=1, window=10)

    svc2 = RateLimitService(storage=storage)
    with pytest.raises(HTTPException):
        svc2.check_rate_limit(ctx, action="act", limit=1, window=10)


def test_tenant_isolation():
    storage = InMemoryRateLimitStorage()
    svc = RateLimitService(storage=storage)
    ctx_a = _build_context("t_a")
    ctx_b = _build_context("t_b")

    svc.check_rate_limit(ctx_a, action="act", limit=1, window=10)
    svc.check_rate_limit(ctx_b, action="act", limit=1, window=10)
