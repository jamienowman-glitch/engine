from __future__ import annotations

from engines.strategy_lock.repository import (
    InMemoryStrategyLockRepository,
    RoutedStrategyLockRepository,
    StrategyLockRepository,
)


def _default_repo() -> StrategyLockRepository:
    return RoutedStrategyLockRepository()


strategy_lock_repo: StrategyLockRepository = _default_repo()


def set_strategy_lock_repo(repo: StrategyLockRepository) -> None:
    global strategy_lock_repo
    strategy_lock_repo = repo
