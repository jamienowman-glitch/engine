from __future__ import annotations

import os
from typing import Dict, List, Optional, Protocol

from engines.memory.models import Blackboard, SessionMemory


class MemoryRepository(Protocol):
    # Session memory
    def upsert_session(self, session: SessionMemory) -> SessionMemory: ...
    def get_session(self, tenant_id: str, env: str, user_id: str, session_id: str) -> Optional[SessionMemory]: ...
    def append_message(self, tenant_id: str, env: str, user_id: str, session_id: str, message) -> SessionMemory: ...
    # Blackboard
    def write_blackboard(self, board: Blackboard) -> Blackboard: ...
    def get_blackboard(self, tenant_id: str, env: str, key: str) -> Optional[Blackboard]: ...
    def delete_blackboard(self, tenant_id: str, env: str, key: str) -> None: ...


class InMemoryMemoryRepository:
    def __init__(self) -> None:
        self._sessions: Dict[tuple[str, str, str, str], SessionMemory] = {}
        self._boards: Dict[tuple[str, str, str], Blackboard] = {}

    def upsert_session(self, session: SessionMemory) -> SessionMemory:
        self._sessions[(session.tenant_id, session.env, session.user_id, session.session_id)] = session
        return session

    def get_session(self, tenant_id: str, env: str, user_id: str, session_id: str) -> Optional[SessionMemory]:
        return self._sessions.get((tenant_id, env, user_id, session_id))

    def append_message(self, tenant_id: str, env: str, user_id: str, session_id: str, message) -> SessionMemory:
        session = self.get_session(tenant_id, env, user_id, session_id)
        if not session:
            session = SessionMemory(tenant_id=tenant_id, env=env, user_id=user_id, session_id=session_id)
        session.messages.append(message)
        session.updated_at = message.timestamp
        self.upsert_session(session)
        return session

    def write_blackboard(self, board: Blackboard) -> Blackboard:
        self._boards[(board.tenant_id, board.env, board.key)] = board
        return board

    def get_blackboard(self, tenant_id: str, env: str, key: str) -> Optional[Blackboard]:
        return self._boards.get((tenant_id, env, key))

    def delete_blackboard(self, tenant_id: str, env: str, key: str) -> None:
        self._boards.pop((tenant_id, env, key), None)


class FirestoreMemoryRepository(InMemoryMemoryRepository):
    """Firestore implementation."""

    def __init__(self, client: Optional[object] = None) -> None:  # pragma: no cover - optional dep
        try:
            from google.cloud import firestore  # type: ignore
        except Exception as exc:
            raise RuntimeError("google-cloud-firestore not installed") from exc
        from engines.config import runtime_config

        project = runtime_config.get_firestore_project()
        if not project:
            raise RuntimeError("GCP project is required for Firestore memory repo")
        self._client = client or firestore.Client(project=project)  # type: ignore[arg-type]
        self._sessions_col = "memory_sessions"
        self._boards_col = "memory_blackboards"

    def _session_doc(self, tenant_id: str, env: str, user_id: str, session_id: str):
        return self._client.collection(self._sessions_col).document(f"{tenant_id}_{env}_{user_id}_{session_id}")

    def _board_doc(self, tenant_id: str, env: str, key: str):
        return self._client.collection(self._boards_col).document(f"{tenant_id}_{env}_{key}")

    def upsert_session(self, session: SessionMemory) -> SessionMemory:
        self._session_doc(session.tenant_id, session.env, session.user_id, session.session_id).set(session.model_dump())
        return session

    def get_session(self, tenant_id: str, env: str, user_id: str, session_id: str) -> Optional[SessionMemory]:
        snap = self._session_doc(tenant_id, env, user_id, session_id).get()
        return SessionMemory(**snap.to_dict()) if snap and snap.exists else None

    def append_message(self, tenant_id: str, env: str, user_id: str, session_id: str, message) -> SessionMemory:
        session = self.get_session(tenant_id, env, user_id, session_id)
        if not session:
            session = SessionMemory(tenant_id=tenant_id, env=env, user_id=user_id, session_id=session_id)
        session.messages.append(message)
        session.updated_at = message.timestamp
        self.upsert_session(session)
        return session

    def write_blackboard(self, board: Blackboard) -> Blackboard:
        self._board_doc(board.tenant_id, board.env, board.key).set(board.model_dump())
        return board

    def get_blackboard(self, tenant_id: str, env: str, key: str) -> Optional[Blackboard]:
        snap = self._board_doc(tenant_id, env, key).get()
        return Blackboard(**snap.to_dict()) if snap and snap.exists else None

    def delete_blackboard(self, tenant_id: str, env: str, key: str) -> None:
        self._board_doc(tenant_id, env, key).delete()


def memory_repo_from_env() -> MemoryRepository:
    backend = os.getenv("MEMORY_BACKEND", "").lower()
    if backend == "firestore":
        try:
            return FirestoreMemoryRepository()
        except Exception:
            return InMemoryMemoryRepository()
    return InMemoryMemoryRepository()
