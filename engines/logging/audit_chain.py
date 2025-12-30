"""Audit hash chain helpers for Gate2."""
from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Protocol

try:
    from google.cloud import firestore  # pragma: no cover - optional
except Exception:  # pragma: no cover
    firestore = None

from engines.common.identity import RequestContext
from engines.dataset.events.schemas import DatasetEvent
from engines.logging.events.contract import (
    DEFAULT_DATASET_SCHEMA_VERSION,
    EventSeverity,
    StorageClass,
    event_contract_enforced,
)

_SANITIZE_PATTERN = re.compile(r"[^A-Za-z0-9_-]+")


def _sanitize(value: str | None) -> str:
    if not value:
        return "unknown"
    return _SANITIZE_PATTERN.sub("_", value)


def _hash_payload(payload: Dict[str, Any], prev_hash: str) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256()
    digest.update(prev_hash.encode("utf-8"))
    digest.update(b"|")
    digest.update(body.encode("utf-8"))
    return digest.hexdigest()


@dataclass(frozen=True)
class AuditScope:
    tenant_id: str
    mode: str
    project_id: str

    def parts(self) -> tuple[str, str, str]:
        return (_sanitize(self.tenant_id), _sanitize(self.mode), _sanitize(self.project_id))


@dataclass
class AuditRecord:
    record_id: str
    payload: Dict[str, Any]
    prev_hash: str
    hash: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
            "hash": self.hash,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditRecord":
        return cls(
            record_id=data["record_id"],
            payload=data["payload"],
            prev_hash=data["prev_hash"],
            hash=data["hash"],
            timestamp=data["timestamp"],
        )


class AuditRepository(Protocol):
    backend_name: str

    def append(self, scope: AuditScope, record: AuditRecord) -> None:
        ...

    def list_records(self, scope: AuditScope) -> list[AuditRecord]:
        ...


class FileAuditRepository:
    backend_name = "audit-filesystem"

    def __init__(self, base_dir: Optional[str | Path] = None) -> None:
        default_dir = Path(base_dir or Path.cwd() / "var" / "audit")
        self._base_dir = Path(default_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _scope_file(self, scope: AuditScope) -> Path:
        parts = scope.parts()
        path = self._base_dir.joinpath(*parts, "audit.log")
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def append(self, scope: AuditScope, record: AuditRecord) -> None:
        path = self._scope_file(scope)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict()))
            handle.write("\n")

    def list_records(self, scope: AuditScope) -> list[AuditRecord]:
        path = self._scope_file(scope)
        if not path.exists():
            return []
        records: list[AuditRecord] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            records.append(AuditRecord.from_dict(data))
        return records

    def path_for_scope(self, scope: AuditScope) -> Path:
        return self._scope_file(scope)


class FirestoreAuditRepository:
    backend_name = "audit-firestore"
    COLLECTION = "audit_chain"

    def __init__(self, client: Any | None = None) -> None:
        if firestore is None:
            raise RuntimeError("google-cloud-firestore is required for the Firestore audit backend")
        self._client = client or firestore.Client()
        self._collection = self._client.collection(self.COLLECTION)

    def append(self, scope: AuditScope, record: AuditRecord) -> None:
        doc_ref = self._collection.document(record.record_id)
        doc_ref.set(
            {
                "scope": {
                    "tenant_id": scope.tenant_id,
                    "mode": scope.mode,
                    "project_id": scope.project_id,
                },
                "record": record.to_dict(),
            }
        )

    def list_records(self, scope: AuditScope) -> list[AuditRecord]:
        query = (
            self._collection.where("scope.tenant_id", "==", scope.tenant_id)
            .where("scope.mode", "==", scope.mode)
            .where("scope.project_id", "==", scope.project_id)
            .order_by("record.timestamp")
        )
        records: list[AuditRecord] = []
        for snapshot in query.stream():
            payload = snapshot.to_dict()
            record_payload = payload.get("record") or {}
            records.append(AuditRecord.from_dict(record_payload))
        return records


def audit_repo_from_env() -> AuditRepository:
    backend = (os.getenv("AUDIT_BACKEND") or "filesystem").lower()
    if backend == "firestore":
        return FirestoreAuditRepository()
    if backend in {"filesystem", "fs"}:
        audit_dir = os.getenv("AUDIT_DIR")
        return FileAuditRepository(base_dir=audit_dir)
    raise RuntimeError("AUDIT_BACKEND must be 'firestore' or 'filesystem'")


class AuditChainService:
    """Append-only audit chain that records DatasetEvents with prev hash links."""

    def __init__(self, repository: AuditRepository | None = None) -> None:
        self._repo = repository or audit_repo_from_env()

    def record_event(
        self,
        ctx: RequestContext,
        action: str,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        run_id: Optional[str] = None,
        step_id: Optional[str] = None,
        severity: EventSeverity = EventSeverity.INFO,
        schema_version: str = DEFAULT_DATASET_SCHEMA_VERSION,
    ) -> AuditRecord:
        scope = self._scope_from_context(ctx)
        prev_hash = self._last_hash(scope)
        payload = self._build_event_payload(
            ctx=ctx,
            action=action,
            input_data=input_data or {},
            output_data=output_data or {},
            metadata=metadata or {},
            trace_id=trace_id,
            run_id=run_id,
            step_id=step_id,
            severity=severity,
            schema_version=schema_version,
        )
        current_hash = _hash_payload(payload, prev_hash)
        record = AuditRecord(
            record_id=str(uuid.uuid4()),
            payload=payload,
            prev_hash=prev_hash,
            hash=current_hash,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._repo.append(scope, record)
        return record

    def verify_chain(self, ctx: RequestContext) -> list[AuditRecord]:
        scope = self._scope_from_context(ctx)
        records = self._repo.list_records(scope)
        prev = ""
        for record in records:
            if record.prev_hash != prev:
                raise RuntimeError(f"unexpected prev_hash for record {record.record_id}")
            expected = _hash_payload(record.payload, prev)
            if record.hash != expected:
                raise RuntimeError(f"hash mismatch for record {record.record_id}")
            prev = record.hash
        return records

    def _scope_from_context(self, ctx: RequestContext) -> AuditScope:
        return AuditScope(
            tenant_id=ctx.tenant_id,
            mode=ctx.mode or ctx.env or "dev",
            project_id=ctx.project_id,
        )

    def _build_event_payload(
        self,
        ctx: RequestContext,
        action: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        metadata: Dict[str, Any],
        trace_id: Optional[str],
        run_id: Optional[str],
        step_id: Optional[str],
        severity: EventSeverity,
        schema_version: str,
    ) -> Dict[str, Any]:
        trace = trace_id or ctx.request_id
        run = run_id or ctx.request_id
        step = step_id or ctx.request_id
        metadata = {**metadata}
        metadata.setdefault("action", action)
        metadata.setdefault("correlation_id", trace)
        metadata.update(
            {
                "tenant_id": ctx.tenant_id,
                "mode": ctx.mode or ctx.env or "dev",
                "project_id": ctx.project_id,
            }
        )
        event = DatasetEvent(
            tenantId=ctx.tenant_id,
            env=ctx.env,
            surface="audit",
            agentId=ctx.user_id or "system",
            input=input_data,
            output=output_data,
            metadata=metadata,
            traceId=trace,
            requestId=ctx.request_id,
            actorType="human" if ctx.user_id else "system",
            mode=ctx.mode,
            project_id=ctx.project_id,
            surface_id=ctx.surface_id,
            app_id=ctx.app_id,
            run_id=run,
            step_id=step,
            schema_version=schema_version,
            severity=severity,
            storage_class=StorageClass.AUDIT,
        )
        if event_contract_enforced():
            event.mode = event.mode or ctx.env
        return event.model_dump()

    def _last_hash(self, scope: AuditScope) -> str:
        records = self._repo.list_records(scope)
        if not records:
            return ""
        return records[-1].hash
