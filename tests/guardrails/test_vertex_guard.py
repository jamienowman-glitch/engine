from __future__ import annotations

import pytest

from engines.cost.vertex_guard import ALLOW_BILLABLE_VERTEX_ENV, ensure_billable_vertex_allowed


def test_vertex_guard_denies_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ALLOW_BILLABLE_VERTEX_ENV, raising=False)
    with pytest.raises(RuntimeError) as excinfo:
        ensure_billable_vertex_allowed("Vertex test")
    assert ALLOW_BILLABLE_VERTEX_ENV in str(excinfo.value)


def test_vertex_guard_allows_with_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ALLOW_BILLABLE_VERTEX_ENV, "1")
    ensure_billable_vertex_allowed("Vertex test")
