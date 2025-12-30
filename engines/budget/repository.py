from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Protocol

from engines.budget.models import UsageEvent


class BudgetUsageRepository(Protocol):
    def record_usage(self, event: UsageEvent) -> UsageEvent: ...
    def list_usage(
        self,
        tenant_id: str,
        env: str,
        surface: Optional[str] = None,
        provider: Optional[str] = None,
        model_or_plan_id: Optional[str] = None,
        tool_type: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> List[UsageEvent]: ...
    def get_totals(
        self,
        tenant_id: str,
        env: str,
        since: datetime,
        until: datetime,
        surface: Optional[str] = None,
        group_by: Optional[str] = None,
    ) -> Dict[str, object]: ...


class InMemoryBudgetUsageRepository:
    def __init__(self) -> None:
        self._items: List[UsageEvent] = []

    def record_usage(self, event: UsageEvent) -> UsageEvent:
        self._items.append(event)
        return event

    def list_usage(
        self,
        tenant_id: str,
        env: str,
        surface: Optional[str] = None,
        provider: Optional[str] = None,
        model_or_plan_id: Optional[str] = None,
        tool_type: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> List[UsageEvent]:
        since = since or datetime.fromtimestamp(0, tz=timezone.utc)
        until = until or datetime.now(timezone.utc)
        items = []
        for ev in self._items:
            if ev.tenant_id != tenant_id or ev.env != env:
                continue
            if surface and ev.surface != surface:
                continue
            if provider and ev.provider != provider:
                continue
            if model_or_plan_id and ev.model_or_plan_id != model_or_plan_id:
                continue
            if tool_type and ev.tool_type != tool_type:
                continue
            if not (since <= ev.created_at <= until):
                continue
            items.append(ev)
        return items[offset : offset + limit]

    def get_totals(
        self,
        tenant_id: str,
        env: str,
        since: datetime,
        until: datetime,
        surface: Optional[str] = None,
        group_by: Optional[str] = None,
    ) -> Dict[str, object]:
        events = self.list_usage(tenant_id, env, surface=surface, since=since, until=until, limit=10_000)
        total_cost = sum([ev.cost for ev in events], start=0)
        total_calls = len(events)
        grouped: Dict[str, Dict[str, object]] = {}
        if group_by:
            for ev in events:
                key = getattr(ev, group_by, None) or "unknown"
                agg = grouped.setdefault(key, {"cost": 0, "count": 0})
                agg["cost"] += ev.cost
                agg["count"] += 1
        return {"total_cost": total_cost, "total_events": total_calls, "grouped": grouped}


class FilesystemBudgetUsageRepository(BudgetUsageRepository):
    """Filesystem-backed usage repo (testable durable backend)."""

    def __init__(self, root: Optional[str] = None) -> None:
        dir_path = root or os.getenv("BUDGET_BACKEND_FS_DIR")
        self._root = Path(dir_path or Path(tempfile.gettempdir()) / "budget_usage")
        self._root.mkdir(parents=True, exist_ok=True)

    def _file_path(self, tenant_id: str, env: str) -> Path:
        name = f"{tenant_id}_{env}.jsonl"
        return self._root / name

    def _load_events(self, tenant_id: str, env: str) -> List[UsageEvent]:
        path = self._file_path(tenant_id, env)
        if not path.exists():
            return []
        events: List[UsageEvent] = []
        with path.open("r", encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                data = json.loads(raw)
                events.append(UsageEvent(**data))
        return events

    def _apply_filters(
        self,
        events: List[UsageEvent],
        surface: Optional[str],
        provider: Optional[str],
        model_or_plan_id: Optional[str],
        tool_type: Optional[str],
        since: Optional[datetime],
        until: Optional[datetime],
    ) -> List[UsageEvent]:
        since = since or datetime.fromtimestamp(0, tz=timezone.utc)
        until = until or datetime.now(timezone.utc)
        filtered = []
        for ev in events:
            if surface and ev.surface != surface:
                continue
            if provider and ev.provider != provider:
                continue
            if model_or_plan_id and ev.model_or_plan_id != model_or_plan_id:
                continue
            if tool_type and ev.tool_type != tool_type:
                continue
            if not (since <= ev.created_at <= until):
                continue
            filtered.append(ev)
        return filtered

    def record_usage(self, event: UsageEvent) -> UsageEvent:
        path = self._file_path(event.tenant_id, event.env)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(event.model_dump_json() + "\n")
        return event

    def list_usage(
        self,
        tenant_id: str,
        env: str,
        surface: Optional[str] = None,
        provider: Optional[str] = None,
        model_or_plan_id: Optional[str] = None,
        tool_type: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> List[UsageEvent]:
        events = self._load_events(tenant_id, env)
        filtered = self._apply_filters(events, surface, provider, model_or_plan_id, tool_type, since, until)
        return filtered[offset : offset + limit]

    def get_totals(
        self,
        tenant_id: str,
        env: str,
        since: datetime,
        until: datetime,
        surface: Optional[str] = None,
        group_by: Optional[str] = None,
    ) -> Dict[str, object]:
        events = self.list_usage(
            tenant_id,
            env,
            surface=surface,
            since=since,
            until=until,
            limit=10_000,
        )
        total_cost = sum([ev.cost for ev in events], start=0)
        total_calls = len(events)
        grouped: Dict[str, Dict[str, object]] = {}
        if group_by:
            for ev in events:
                key = getattr(ev, group_by, None) or "unknown"
                agg = grouped.setdefault(key, {"cost": 0, "count": 0})
                agg["cost"] += ev.cost
                agg["count"] += 1
        return {"total_cost": total_cost, "total_events": total_calls, "grouped": grouped}


class FirestoreBudgetUsageRepository(InMemoryBudgetUsageRepository):
    """Firestore-backed usage repo."""

    def __init__(self, client: Optional[object] = None) -> None:  # pragma: no cover - optional dep
        try:
            from google.cloud import firestore  # type: ignore
        except Exception as exc:
            raise RuntimeError("google-cloud-firestore not installed") from exc
        from engines.config import runtime_config

        project = runtime_config.get_firestore_project()
        if not project:
            raise RuntimeError("GCP project is required for Firestore budget usage repo")
        self._client = client or firestore.Client(project=project)  # type: ignore[arg-type]
        self._root_collection = "budget_usage"

    def _events_col(self, tenant_id: str, env: str):
        doc = self._client.collection(self._root_collection).document(f"{tenant_id}_{env}")
        return doc.collection("events")

    def record_usage(self, event: UsageEvent) -> UsageEvent:
        self._events_col(event.tenant_id, event.env).document(event.id).set(event.model_dump())
        return event

    def list_usage(
        self,
        tenant_id: str,
        env: str,
        surface: Optional[str] = None,
        provider: Optional[str] = None,
        model_or_plan_id: Optional[str] = None,
        tool_type: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> List[UsageEvent]:
        col = self._events_col(tenant_id, env)
        query = col
        if surface:
            query = query.where("surface", "==", surface)
        if provider:
            query = query.where("provider", "==", provider)
        if model_or_plan_id:
            query = query.where("model_or_plan_id", "==", model_or_plan_id)
        if tool_type:
            query = query.where("tool_type", "==", tool_type)
        if since:
            query = query.where("created_at", ">=", since)
        if until:
            query = query.where("created_at", "<=", until)
        docs = query.limit(limit + offset).stream()
        events = [UsageEvent(**d.to_dict()) for d in docs]
        return events[offset : offset + limit]

    def get_totals(
        self,
        tenant_id: str,
        env: str,
        since: datetime,
        until: datetime,
        surface: Optional[str] = None,
        group_by: Optional[str] = None,
    ) -> Dict[str, object]:
        events = self.list_usage(tenant_id, env, surface=surface, since=since, until=until, limit=10_000)
        total_cost = sum([ev.cost for ev in events], start=0)
        total_calls = len(events)
        grouped: Dict[str, Dict[str, object]] = {}
        if group_by:
            for ev in events:
                key = getattr(ev, group_by, None) or "unknown"
                agg = grouped.setdefault(key, {"cost": 0, "count": 0})
                agg["cost"] += ev.cost
                agg["count"] += 1
        return {"total_cost": total_cost, "total_events": total_calls, "grouped": grouped}


def budget_repo_from_env() -> BudgetUsageRepository:
    backend = os.getenv("BUDGET_BACKEND", "").lower()
    if backend == "firestore":
        try:
            return FirestoreBudgetUsageRepository()
        except Exception as exc:
            raise RuntimeError(f"BUDGET_BACKEND=firestore failed to initialize: {exc}") from exc
    if backend == "filesystem":
        root = os.getenv("BUDGET_BACKEND_FS_DIR")
        return FilesystemBudgetUsageRepository(root=root)
    raise RuntimeError("BUDGET_BACKEND must be set to a durable backend (firestore|filesystem)")
