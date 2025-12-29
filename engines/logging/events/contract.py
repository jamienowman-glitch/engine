"""Shared envelope helpers for compliance runs."""
from __future__ import annotations

import os
from enum import Enum
from typing import Iterable

EVENT_CONTRACT_ENV = "EVENT_CONTRACT_ENFORCE"
COMPLIANCE_RUN_ENV = "EVENT_CONTRACT_COMPLIANCE"

DEFAULT_DATASET_SCHEMA_VERSION = "1"
DEFAULT_STREAM_SCHEMA_VERSION = "1"


class StorageClass(str, Enum):
    OPS = "ops"
    AUDIT = "audit"
    STREAM = "stream"
    COST = "cost"

    @classmethod
    def values(cls) -> Iterable[str]:
        return (member.value for member in cls)


class EventSeverity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    @classmethod
    def values(cls) -> Iterable[str]:
        return (member.value for member in cls)


def _truthy_env(var: str) -> bool:
    value = os.getenv(var)
    if not value:
        return False
    return value.strip().lower() in {"1", "true", "yes"}


def event_contract_enforced() -> bool:
    return _truthy_env(EVENT_CONTRACT_ENV)


def compliance_run_enabled() -> bool:
    return event_contract_enforced() or _truthy_env(COMPLIANCE_RUN_ENV)
