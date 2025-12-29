from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol

from engines.memory.models import Blackboard, MessageRecord, SessionMemory


def _sanitize_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value or "unknown")


@dataclass(frozen=True)
class SessionScope:
    tenant_id: str
    mode: str
    project_id: str
    user_id: str
    session_id: str


@dataclass(frozen=True)
class BlackboardScope:
    tenant_id: str
    mode: str
    project_id: str
    key: str


class MemoryRepository(Protocol):
    def upsert_session(self, session: SessionMemory) -> SessionMemory: ...

    def get_session(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        user_id: str,
        session_id: str,
    ) -> Optional[SessionMemory]: ...

    def append_message(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        user_id: str,
        session_id: str,
        message: MessageRecord,
    ) -> SessionMemory: ...

    def write_blackboard(self, board: Blackboard) -> Blackboard: ...

    def get_blackboard(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        key: str,
    ) -> Optional[Blackboard]: ...

    def delete_blackboard(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        key: str,
    ) -> None: ...


class FileMemoryRepository(MemoryRepository):
    """Filesystem-backed memory repository scoped by tenant/mode/project/user/session."""

    def __init__(self, base_dir: Optional[str] = None) -> None:
        default_dir = Path(os.getenv("MEMORY_DIR") or Path.cwd() / "var" / "memory")
        self._base_dir = Path(base_dir) if base_dir else default_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, scope: SessionScope) -> Path:
        filename = "__".join(
            _sanitize_name(value)
            for value in (
                scope.tenant_id,
                scope.mode,
                scope.project_id,
                scope.user_id,
                scope.session_id,
            )
        )
        path = self._base_dir / "sessions" / f"{filename}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _board_path(self, scope: BlackboardScope) -> Path:
        filename = "__".join(
            _sanitize_name(value)
            for value in (
                scope.tenant_id,
                scope.mode,
                scope.project_id,
                scope.key,
            )
        )
        path = self._base_dir / "blackboards" / f"{filename}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def upsert_session(self, session: SessionMemory) -> SessionMemory:
        path = self._session_path(
            SessionScope(
                tenant_id=session.tenant_id,
                mode=session.mode,
                project_id=session.project_id,
                user_id=session.user_id,
                session_id=session.session_id,
            )
        )
        with path.open("w", encoding="utf-8") as handle:
            json.dump(session.model_dump(), handle, indent=2, default=str)
        return session

    def get_session(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        user_id: str,
        session_id: str,
    ) -> Optional[SessionMemory]:
        path = self._session_path(
            SessionScope(
                tenant_id=tenant_id,
                mode=mode,
                project_id=project_id,
                user_id=user_id,
                session_id=session_id,
            )
        )
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return SessionMemory(**data)

    def append_message(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        user_id: str,
        session_id: str,
        message: MessageRecord,
    ) -> SessionMemory:
        session = self.get_session(tenant_id, mode, project_id, user_id, session_id)
        if not session:
            session = SessionMemory(
                tenant_id=tenant_id,
                mode=mode,
                project_id=project_id,
                user_id=user_id,
                session_id=session_id,
            )
        session.messages.append(message)
        session.updated_at = message.timestamp
        self.upsert_session(session)
        return session

    def write_blackboard(self, board: Blackboard) -> Blackboard:
        path = self._board_path(
            BlackboardScope(
                tenant_id=board.tenant_id,
                mode=board.mode,
                project_id=board.project_id,
                key=board.key,
            )
        )
        with path.open("w", encoding="utf-8") as handle:
            json.dump(board.model_dump(), handle, indent=2, default=str)
        return board

    def get_blackboard(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        key: str,
    ) -> Optional[Blackboard]:
        path = self._board_path(
            BlackboardScope(
                tenant_id=tenant_id,
                mode=mode,
                project_id=project_id,
                key=key,
            )
        )
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return Blackboard(**data)

    def delete_blackboard(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        key: str,
    ) -> None:
        path = self._board_path(
            BlackboardScope(
                tenant_id=tenant_id,
                mode=mode,
                project_id=project_id,
                key=key,
            )
        )
        if path.exists():
            path.unlink()


class FirestoreMemoryRepository(MemoryRepository):
    """Firestore implementation (durable only)."""

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

    def _session_doc(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        user_id: str,
        session_id: str,
    ):
        key = f"{tenant_id}_{mode}_{project_id}_{user_id}_{session_id}"
        return self._client.collection(self._sessions_col).document(key)

    def _board_doc(self, tenant_id: str, mode: str, project_id: str, key: str):
        doc_id = f"{tenant_id}_{mode}_{project_id}_{key}"
        return self._client.collection(self._boards_col).document(doc_id)

    def upsert_session(self, session: SessionMemory) -> SessionMemory:
        self._session_doc(
            session.tenant_id,
            session.mode,
            session.project_id,
            session.user_id,
            session.session_id,
        ).set(session.model_dump())
        return session

    def get_session(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        user_id: str,
        session_id: str,
    ) -> Optional[SessionMemory]:
        snap = self._session_doc(tenant_id, mode, project_id, user_id, session_id).get()
        return SessionMemory(**snap.to_dict()) if snap and snap.exists else None

    def append_message(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        user_id: str,
        session_id: str,
        message: MessageRecord,
    ) -> SessionMemory:
        session = self.get_session(tenant_id, mode, project_id, user_id, session_id)
        if not session:
            session = SessionMemory(
                tenant_id=tenant_id,
                mode=mode,
                project_id=project_id,
                user_id=user_id,
                session_id=session_id,
            )
        session.messages.append(message)
        session.updated_at = message.timestamp
        self.upsert_session(session)
        return session

    def write_blackboard(self, board: Blackboard) -> Blackboard:
        self._board_doc(board.tenant_id, board.mode, board.project_id, board.key).set(board.model_dump())
        return board

    def get_blackboard(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        key: str,
    ) -> Optional[Blackboard]:
        snap = self._board_doc(tenant_id, mode, project_id, key).get()
        return Blackboard(**snap.to_dict()) if snap and snap.exists else None

    def delete_blackboard(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        key: str,
    ) -> None:
        self._board_doc(tenant_id, mode, project_id, key).delete()


def memory_repo_from_env() -> MemoryRepository:
    backend = os.getenv("MEMORY_BACKEND", "").lower()
    if backend == "firestore":
        try:
            return FirestoreMemoryRepository()
        except Exception as exc:
            raise RuntimeError(f"MEMORY_BACKEND=firestore failed to initialize: {exc}") from exc
    if backend in {"filesystem", "fs"}:
        storage_dir = os.getenv("MEMORY_DIR")
        if not storage_dir:
            raise RuntimeError("MEMORY_DIR is required for filesystem memory backend")
        return FileMemoryRepository(base_dir=storage_dir)
    raise RuntimeError("MEMORY_BACKEND must be set to 'firestore' or 'filesystem'")
