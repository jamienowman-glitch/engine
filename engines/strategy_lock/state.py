from __future__ import annotations

import os

from engines.strategy_lock.repository import InMemoryStrategyLockRepository, StrategyLockRepository, FirestoreStrategyLockRepository


def _default_repo() -> StrategyLockRepository:
    backend = os.getenv("STRATEGY_LOCK_BACKEND", "").lower()
    if backend == "firestore":
        try:
            return FirestoreStrategyLockRepository()
        except NotImplementedError:
            # Fall back until Firestore impl lands
            return InMemoryStrategyLockRepository()
    return InMemoryStrategyLockRepository()


strategy_lock_repo: StrategyLockRepository = _default_repo()


def set_strategy_lock_repo(repo: StrategyLockRepository) -> None:
    global strategy_lock_repo
    strategy_lock_repo = repo
