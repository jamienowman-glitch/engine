"""Storage abstractions for Maybes notes."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Protocol

from engines.maybes.schemas import MaybesNote


class MaybesRepository(Protocol):
    def save(self, note: MaybesNote) -> MaybesNote:
        ...

    def get(self, maybes_id: str) -> MaybesNote | None:
        ...

    def list_for_user(self, tenant_id: str, user_id: str) -> Iterable[MaybesNote]:
        ...


class InMemoryMaybesRepository:
    """Simple in-memory repository for tests and dev."""

    def __init__(self) -> None:
        self._notes: Dict[str, MaybesNote] = {}

    def save(self, note: MaybesNote) -> MaybesNote:
        self._notes[note.maybes_id] = note
        return note

    def get(self, maybes_id: str) -> MaybesNote | None:
        return self._notes.get(maybes_id)

    def list_for_user(self, tenant_id: str, user_id: str) -> List[MaybesNote]:
        return [
            n for n in self._notes.values() if n.tenant_id == tenant_id and n.user_id == user_id
        ]


def get_maybes_repository(client: Any = None) -> MaybesRepository:
    """Return a repository, preferring Firestore when available."""
    try:
        from engines.maybes.firestore_repository import FirestoreMaybesRepository

        return FirestoreMaybesRepository(client=client)
    except Exception:
        return InMemoryMaybesRepository()
