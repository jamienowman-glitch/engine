"""Blackboard store module (Agent A).

Provides persistent shared coordination state with versioning and optimistic concurrency.
Scope: tenant / mode / project / run.
"""

from engines.blackboard_store.service import BlackboardStoreService
from engines.blackboard_store.service_reject import (
    BlackboardStoreServiceRejectOnMissing,
    MissingBlackboardStoreRoute,
)
from engines.blackboard_store.cloud_blackboard_store import VersionConflictError

__all__ = [
    "BlackboardStoreService",
    "BlackboardStoreServiceRejectOnMissing",
    "MissingBlackboardStoreRoute",
    "VersionConflictError",
]
