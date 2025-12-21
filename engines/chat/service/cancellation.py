"""Simple in-memory cancellation for runs (Phase 02)."""
from __future__ import annotations

import logging
from typing import Set

logger = logging.getLogger(__name__)

# Global set of run_ids that should stop
_CANCELLED_RUNS: Set[str] = set()

def cancel_run(run_id: str) -> None:
    _CANCELLED_RUNS.add(run_id)
    logger.info(f"Cancellation requested for run_id={run_id}")

def is_cancelled(run_id: str) -> bool:
    return run_id in _CANCELLED_RUNS

def clear_cancellation(run_id: str) -> None:
    if run_id in _CANCELLED_RUNS:
        _CANCELLED_RUNS.remove(run_id)
