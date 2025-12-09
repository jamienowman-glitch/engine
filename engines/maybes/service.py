"""Service for Maybes scratchpad notes."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Sequence

from engines.logging.event_log import EventLogEntry, EventLogger, default_event_logger
from engines.maybes.repository import InMemoryMaybesRepository, MaybesRepository, get_maybes_repository
from engines.maybes.schemas import MaybesFilters, MaybesNote


class MaybesError(Exception):
    """Base error for Maybes operations."""


class MaybesNotFound(MaybesError):
    """Raised when a note is not found."""


class MaybesForbidden(MaybesError):
    """Raised when tenant/user mismatch occurs."""


@dataclass
class CanvasLayoutUpdate:
    maybes_id: str
    layout_x: float
    layout_y: float
    layout_scale: float


class MaybesService:
    def __init__(
        self,
        repository: Optional[MaybesRepository] = None,
        event_logger: Optional[EventLogger] = None,
    ) -> None:
        self._repo = repository or get_maybes_repository()
        self._event_logger = event_logger or default_event_logger

    def create_note(
        self,
        tenant_id: str,
        user_id: str,
        body: str,
        title: Optional[str] = None,
        colour_token: Optional[str] = None,
        tags: Optional[Sequence[str]] = None,
        origin_ref: Optional[Dict] = None,
        episode_id: Optional[str] = None,
        layout_x: float = 0.0,
        layout_y: float = 0.0,
        layout_scale: float = 1.0,
    ) -> MaybesNote:
        note = MaybesNote(
            tenant_id=tenant_id,
            user_id=user_id,
            body=body,
            title=title,
            colour_token=colour_token,
            tags=list(tags or []),
            origin_ref=origin_ref or {},
            episode_id=episode_id,
            layout_x=layout_x,
            layout_y=layout_y,
            layout_scale=layout_scale,
        )
        self._repo.save(note)
        self._log_event("maybes_created", note)
        return note

    def update_note(
        self,
        maybes_id: str,
        tenant_id: str,
        user_id: str,
        patch: Dict,
    ) -> MaybesNote:
        note = self._require_note(maybes_id, tenant_id, user_id)
        allowed_fields = {
            "title",
            "body",
            "colour_token",
            "tags",
            "origin_ref",
            "is_pinned",
            "is_archived",
            "layout_x",
            "layout_y",
            "layout_scale",
            "episode_id",
            "nexus_doc_id",
        }
        changed = False
        for key, value in patch.items():
            if key not in allowed_fields:
                continue
            setattr(note, key, value)
            changed = True
        if changed:
            note.updated_at = datetime.now(timezone.utc)
            self._repo.save(note)
            self._log_event("maybes_updated", note)
        return note

    def archive_note(self, maybes_id: str, tenant_id: str, user_id: str) -> MaybesNote:
        note = self._require_note(maybes_id, tenant_id, user_id)
        if not note.is_archived:
            note.is_archived = True
            note.updated_at = datetime.now(timezone.utc)
            self._repo.save(note)
            self._log_event("maybes_archived", note)
        return note

    def get_note(self, maybes_id: str, tenant_id: str, user_id: str) -> MaybesNote:
        return self._require_note(maybes_id, tenant_id, user_id)

    def list_notes(
        self, tenant_id: str, user_id: str, filters: Optional[MaybesFilters] = None
    ) -> List[MaybesNote]:
        filters = filters or MaybesFilters()
        candidates = list(self._repo.list_for_user(tenant_id, user_id))
        results: List[MaybesNote] = []
        search_term = filters.search.lower() if filters.search else None
        for note in candidates:
            if note.is_archived and not filters.include_archived:
                continue
            if filters.tags and not set(filters.tags).issubset(set(note.tags)):
                continue
            if search_term and search_term not in (note.body.lower() + " " + (note.title or "").lower()):
                continue
            if filters.created_after and note.created_at < filters.created_after:
                continue
            if filters.created_before and note.created_at > filters.created_before:
                continue
            if filters.origin_ref:
                if not _origin_matches(note.origin_ref, filters.origin_ref):
                    continue
            results.append(note)
        return results

    def save_canvas_layout(
        self, tenant_id: str, user_id: str, layouts: Iterable[CanvasLayoutUpdate]
    ) -> List[Dict[str, float | str]]:
        updated = []
        now = datetime.now(timezone.utc)
        for layout in layouts:
            note = self._require_note(layout.maybes_id, tenant_id, user_id)
            note.layout_x = layout.layout_x
            note.layout_y = layout.layout_y
            note.layout_scale = layout.layout_scale
            note.updated_at = now
            self._repo.save(note)
            updated.append(
                {
                    "maybes_id": note.maybes_id,
                    "layout_x": note.layout_x,
                    "layout_y": note.layout_y,
                    "layout_scale": note.layout_scale,
                }
            )
            self._log_event("maybes_updated", note)
        return updated

    def get_canvas_layout(self, tenant_id: str, user_id: str) -> List[Dict[str, float | str]]:
        notes = self.list_notes(tenant_id, user_id, MaybesFilters(include_archived=False))
        return [
            {
                "maybes_id": n.maybes_id,
                "layout_x": n.layout_x,
                "layout_y": n.layout_y,
                "layout_scale": n.layout_scale,
            }
            for n in notes
        ]

    def _require_note(self, maybes_id: str, tenant_id: str, user_id: str) -> MaybesNote:
        note = self._repo.get(maybes_id)
        if not note:
            raise MaybesNotFound(f"note {maybes_id} not found")
        if note.tenant_id != tenant_id or note.user_id != user_id:
            raise MaybesForbidden("note does not belong to tenant/user")
        return note

    def _log_event(self, event_type: str, note: Optional[MaybesNote]) -> None:
        if not note or not self._event_logger:
            return
        entry = EventLogEntry(
            event_type=event_type,
            asset_type=note.asset_type,
            asset_id=note.maybes_id,
            tenant_id=note.tenant_id,
            user_id=note.user_id,
            origin_ref=note.origin_ref,
            episode_id=note.episode_id,
            surface="maybes",
        )
        self._event_logger(entry)


def _origin_matches(current: Dict, required: Dict) -> bool:
    """Return True if all keys in required match values in current."""
    for key, value in required.items():
        if current.get(key) != value:
            return False
    return True
