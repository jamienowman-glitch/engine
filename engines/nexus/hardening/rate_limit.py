"""Rate limiting primitive with optional persistence."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Dict, Optional, Protocol, Tuple

from fastapi import HTTPException

from engines.common.identity import RequestContext
from engines.config import runtime_config

try:  # pragma: no cover - optional dependency
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover
    firestore = None


class RateLimitStorage(Protocol):
    def load(self, key: Tuple[str, str]) -> Optional["RateLimitEntry"]:
        ...

    def save(self, key: Tuple[str, str], entry: "RateLimitEntry") -> None:
        ...


@dataclass
class RateLimitEntry:
    last_reset: float
    count: int


class InMemoryRateLimitStorage:
    def __init__(self) -> None:
        self._store: Dict[Tuple[str, str], RateLimitEntry] = {}

    def load(self, key: Tuple[str, str]) -> Optional[RateLimitEntry]:
        return self._store.get(key)

    def save(self, key: Tuple[str, str], entry: RateLimitEntry) -> None:
        self._store[key] = entry


class FirestoreRateLimitStorage:
    _collection = "rate_limit_counters"

    def __init__(self, client: Optional[object] = None) -> None:
        if firestore is None:
            raise RuntimeError("google-cloud-firestore is required for rate limit persistence")
        project = runtime_config.get_firestore_project()
        if not project:
            raise RuntimeError("GCP project is required for Firestore rate limit backend")
        self._client = client or firestore.Client(project=project)  # type: ignore[arg-type]

    def _doc(self, tenant_id: str, action: str):
        doc_id = f"{tenant_id}__{action}"
        return self._client.collection(self._collection).document(doc_id)

    def load(self, key: Tuple[str, str]) -> Optional[RateLimitEntry]:
        tenant_id, action = key
        snap = self._doc(tenant_id, action).get()
        if not snap or not getattr(snap, "exists", False):
            return None
        data = snap.to_dict() or {}
        return RateLimitEntry(
            last_reset=float(data.get("last_reset", time.time())),
            count=int(data.get("count", 0)),
        )

    def save(self, key: Tuple[str, str], entry: RateLimitEntry) -> None:
        tenant_id, action = key
        self._doc(tenant_id, action).set(
            {"last_reset": entry.last_reset, "count": entry.count}
        )


def _default_storage() -> RateLimitStorage:
    backend = (os.getenv("RATE_LIMIT_BACKEND") or "memory").lower()
    if backend == "firestore":
        try:
            return FirestoreRateLimitStorage()
        except Exception:
            pass
    return InMemoryRateLimitStorage()


DEFAULT_RATE_LIMIT = 100  # requests
DEFAULT_WINDOW = 60.0  # seconds


class RateLimitService:
    def __init__(self, storage: Optional[RateLimitStorage] = None):
        self.storage = storage or _default_storage()

    def check_rate_limit(
        self,
        ctx: RequestContext,
        action: str = "default",
        limit: int = DEFAULT_RATE_LIMIT,
        window: float = DEFAULT_WINDOW,
    ) -> None:
        now = time.time()
        key = (ctx.tenant_id, action)
        entry = self.storage.load(key)
        if not entry or now - entry.last_reset >= window:
            entry = RateLimitEntry(last_reset=now, count=0)

        if entry.count >= limit:
            raise HTTPException(
                status_code=429,
                detail={"error": "rate_limit_exceeded", "limit": limit, "window_seconds": window},
            )

        entry.count += 1
        self.storage.save(key, entry)


_default_limiter = RateLimitService()


def get_rate_limiter() -> RateLimitService:
    return _default_limiter
