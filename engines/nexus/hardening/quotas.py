"""Quota Management primitive."""
from __future__ import annotations

from fastapi import HTTPException

from engines.common.identity import RequestContext

# Mock quota config
# In real prod, this comes from Config or DB
QUOTA_LIMITS = {
    "default": {"storage_bytes": 10_000_000_000, "daily_requests": 100_000},
    "t_free_tier": {"storage_bytes": 100_000_000, "daily_requests": 1000},
}


class QuotaService:
    def check_quota(self, ctx: RequestContext, metric: str, value: int = 1) -> None:
        """
        Check if tenant has quota for metric.
        Stub implementation—real impl would check usage counters.
        """
        # Feature flag / usage check logic here.
        # For Phase 9, we prove the hook exists.
        
        limits = QUOTA_LIMITS.get(ctx.tenant_id, QUOTA_LIMITS["default"])
        limit = limits.get(metric)
        
        if limit is not None and value > limit:
             raise HTTPException(
                status_code=403, 
                detail={"error": "quota_exceeded", "metric": metric, "limit": limit}
            )

_default_quota = QuotaService()

def get_quota_service() -> QuotaService:
    return _default_quota
