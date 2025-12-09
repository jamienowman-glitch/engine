from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from engines.maybes.schemas import MaybesFilters
from engines.maybes.service import (
    CanvasLayoutUpdate,
    MaybesForbidden,
    MaybesNotFound,
    MaybesService,
)


def test_create_update_archive_logs_events():
    events = []
    svc = MaybesService(event_logger=lambda e: events.append(e))
    note = svc.create_note("t_demo", "u1", body="hello", title="note1", tags=["alpha"])
    assert note.asset_type == "maybes_note"
    assert events[-1].event_type == "maybes_created"

    updated = svc.update_note(note.maybes_id, "t_demo", "u1", {"body": "updated", "is_pinned": True})
    assert updated.body == "updated"
    assert updated.is_pinned is True
    assert any(e.event_type == "maybes_updated" for e in events)

    archived = svc.archive_note(note.maybes_id, "t_demo", "u1")
    assert archived.is_archived is True
    assert events[-1].event_type == "maybes_archived"


def test_filters_apply_tags_search_and_dates():
    svc = MaybesService(event_logger=lambda e: None)
    note_recent = svc.create_note("t_demo", "u1", body="alpha body", tags=["alpha"])
    note_old = svc.create_note("t_demo", "u1", body="beta content", tags=["beta"])
    note_old.created_at = datetime.now(timezone.utc) - timedelta(days=10)
    svc._repo.save(note_old)  # type: ignore[attr-defined]

    filters = MaybesFilters(tags=["alpha"])
    results = svc.list_notes("t_demo", "u1", filters)
    assert [n.maybes_id for n in results] == [note_recent.maybes_id]

    filters = MaybesFilters(search="beta")
    results = svc.list_notes("t_demo", "u1", filters)
    assert results and results[0].maybes_id == note_old.maybes_id

    cutoff = datetime.now(timezone.utc) - timedelta(days=5)
    filters = MaybesFilters(created_after=cutoff)
    results = svc.list_notes("t_demo", "u1", filters)
    assert note_recent.maybes_id in {n.maybes_id for n in results}
    assert note_old.maybes_id not in {n.maybes_id for n in results}


def test_canvas_layout_updates_and_logs():
    events = []
    svc = MaybesService(event_logger=lambda e: events.append(e))
    note = svc.create_note("t_demo", "u1", body="layout")
    layouts = svc.save_canvas_layout(
        "t_demo",
        "u1",
        [CanvasLayoutUpdate(maybes_id=note.maybes_id, layout_x=1.5, layout_y=2.5, layout_scale=0.8)],
    )
    assert layouts[0]["layout_x"] == 1.5
    assert any(e.event_type == "maybes_updated" for e in events)


def test_forbidden_and_not_found():
    svc = MaybesService(event_logger=lambda e: None)
    note = svc.create_note("t_demo", "u1", body="secure")
    with pytest.raises(MaybesForbidden):
        svc.get_note(note.maybes_id, "t_demo", "other_user")
    with pytest.raises(MaybesNotFound):
        svc.get_note("missing", "t_demo", "u1")
