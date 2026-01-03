"""Memory store module (Agent A — Memory track).

Provides persistent session memory with configurable TTL.
Scope: tenant / mode / user / session.

MEM-01 compliance: routed-only in saas/enterprise; rejects (HTTP 503) on missing route.
"""

from engines.memory_store.service import MemoryStoreService
from engines.memory_store.service_reject import MemoryStoreServiceRejectOnMissing, MissingMemoryStoreRoute

__all__ = [
    "MemoryStoreService",
    "MemoryStoreServiceRejectOnMissing",
    "MissingMemoryStoreRoute",
]
