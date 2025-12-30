"""Durable knowledge metadata repositories."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Iterable, Protocol

from engines.knowledge.models import KnowledgeDocument, KnowledgeScope

try:
    from google.cloud import firestore  # pragma: no cover - optional
except Exception:  # pragma: no cover
    firestore = None

_SANITIZE_PATTERN = re.compile(r"[^A-Za-z0-9_-]+")


def _sanitize(value: str) -> str:
    return _SANITIZE_PATTERN.sub("_", value or "")


class KnowledgeRepository(Protocol):
    backend_name: str

    def save_document(self, document: KnowledgeDocument) -> None:
        ...

    def list_documents(self, scope: KnowledgeScope) -> list[KnowledgeDocument]:
        ...


class FirestoreKnowledgeRepository:
    backend_name = "bm25-firestore"
    COLLECTION = "knowledge_documents"

    def __init__(self, client: object | None = None) -> None:
        if firestore is None:
            raise RuntimeError("google-cloud-firestore is required for the Firestore knowledge backend")
        self._client = client or firestore.Client()
        self._collection = self._client.collection(self.COLLECTION)

    def save_document(self, document: KnowledgeDocument) -> None:
        self._collection.document(document.doc_id).set(document.to_dict())

    def list_documents(self, scope: KnowledgeScope) -> list[KnowledgeDocument]:
        query = (
            self._collection
            .where("tenant_id", "==", scope.tenant_id)
            .where("mode", "==", scope.mode)
            .where("project_id", "==", scope.project_id)
        )
        if scope.user_id:
            query = query.where("user_id", "==", scope.user_id)
        if scope.session_id:
            query = query.where("session_id", "==", scope.session_id)
        documents = []
        for snapshot in query.stream():
            documents.append(KnowledgeDocument.from_dict(snapshot.to_dict()))
        return documents


class FileKnowledgeRepository:
    backend_name = "bm25-filesystem"

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self._base_dir = Path(base_dir or Path.cwd() / "var" / "knowledge")
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _scope_dir(self, scope: KnowledgeScope) -> Path:
        parts = [scope.tenant_id, scope.mode, scope.project_id]
        if scope.user_id:
            parts.append(scope.user_id)
        if scope.session_id:
            parts.append(scope.session_id)
        safe_parts = [_sanitize(part) for part in parts]
        return self._base_dir.joinpath("tenants", *safe_parts, "docs")

    def save_document(self, document: KnowledgeDocument) -> None:
        target_dir = self._scope_dir(document.scope)
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{_sanitize(document.doc_id)}.json"
        path.write_text(json.dumps(document.to_dict()), encoding="utf-8")

    def list_documents(self, scope: KnowledgeScope) -> list[KnowledgeDocument]:
        directory = self._scope_dir(scope)
        if not directory.exists():
            return []
        documents: list[KnowledgeDocument] = []
        for path in directory.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                documents.append(KnowledgeDocument.from_dict(data))
            except Exception:
                continue
        return documents


def knowledge_repo_from_env() -> KnowledgeRepository:
    backend = (os.getenv("KNOWLEDGE_BACKEND") or "filesystem").lower()
    if backend == "firestore":
        return FirestoreKnowledgeRepository()
    if backend in {"filesystem", "fs"}:
        storage_dir = os.getenv("KNOWLEDGE_DIR")
        return FileKnowledgeRepository(storage_dir)
    raise RuntimeError("KNOWLEDGE_BACKEND must be firestore or filesystem")
