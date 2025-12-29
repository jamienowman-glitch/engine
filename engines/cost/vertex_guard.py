"""Guard to prevent accidental Vertex usage unless explicitly allowed."""

from __future__ import annotations

import os

ALLOW_BILLABLE_VERTEX_ENV = "ALLOW_BILLABLE_VERTEX"
_DOCUMENTATION_PATH = "docs/infra/COST_KILL_SWITCH.md"


def allow_billable_vertex() -> bool:
    """Return True when Vertex billing is explicitly allowed."""
    value = os.getenv(ALLOW_BILLABLE_VERTEX_ENV, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def ensure_billable_vertex_allowed(feature: str) -> None:
    """Raise when billing is denied and refer to the documentation."""
    if allow_billable_vertex():
        return
    raise RuntimeError(
        f"{feature} requires {ALLOW_BILLABLE_VERTEX_ENV}=1 to proceed (see {_DOCUMENTATION_PATH} for context)."
    )
