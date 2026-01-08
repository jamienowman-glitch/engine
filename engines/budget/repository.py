from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Protocol

from engines.budget.models import BudgetPolicy, UsageEvent


class BudgetUsageRepository(Protocol):
    def record_usage(self, event: UsageEvent) -> UsageEvent: ...
    def list_usage(
        self,
        tenant_id: str,
        env: str,
        surface: Optional[str] = None,
        provider: Optional[str] = None,
        tool_id: Optional[str] = None,
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
        tool_id: Optional[str],
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
        filtered = self._apply_filters(events, surface, provider, tool_id, model_or_plan_id, tool_type, since, until)
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
        if tool_id:
            query = query.where("tool_id", "==", tool_id)
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


class BudgetPolicyRepository(Protocol):
    def get_policy(
        self,
        tenant_id: str,
        env: str,
        mode: str,
        surface: Optional[str] = None,
        app: Optional[str] = None,
    ) -> Optional[BudgetPolicy]: ...

    def save_policy(self, policy: BudgetPolicy) -> BudgetPolicy: ...


def _normalize_key(
    tenant_id: str,
    env: str,
    mode: str,
    surface: Optional[str],
    app: Optional[str],
) -> tuple[str, str, str, Optional[str], Optional[str]]:
    normalized_mode = mode.lower()
    return (tenant_id, env, normalized_mode, surface or None, app or None)


class InMemoryBudgetPolicyRepository:
    def __init__(self) -> None:
        self._store: Dict[tuple[str, str, str, Optional[str], Optional[str]], BudgetPolicy] = {}

    def _iter_candidates(
        self,
        tenant_id: str,
        env: str,
        mode: str,
        surface: Optional[str],
        app: Optional[str],
    ) -> tuple[str, str, str, Optional[str], Optional[str]]:
        normalized_surface = surface or None
        normalized_app = app or None
        mode_normalized = mode.lower()
        for candidate_surface, candidate_app in (
            (normalized_surface, normalized_app),
            (normalized_surface, None),
            (None, normalized_app),
            (None, None),
        ):
            yield (tenant_id, env, mode_normalized, candidate_surface, candidate_app)

    def get_policy(
        self,
        tenant_id: str,
        env: str,
        mode: str,
        surface: Optional[str] = None,
        app: Optional[str] = None,
    ) -> Optional[BudgetPolicy]:
        for key in self._iter_candidates(tenant_id, env, mode, surface, app):
            policy = self._store.get(key)
            if policy:
                return policy
        return None

    def save_policy(self, policy: BudgetPolicy) -> BudgetPolicy:
        key = _normalize_key(policy.tenant_id, policy.env, policy.mode, policy.surface, policy.app)
        now = datetime.now(timezone.utc)
        existing = self._store.get(key)
        created = existing.created_at if existing else policy.created_at
        stored = BudgetPolicy(
            tenant_id=policy.tenant_id,
            env=policy.env,
            surface=policy.surface,
            mode=policy.mode,
            app=policy.app,
            threshold=policy.threshold,
            created_at=created,
            updated_at=now,
        )
        self._store[key] = stored
        return stored


class FilesystemBudgetPolicyRepository(BudgetPolicyRepository):
    def __init__(self, root: Optional[str] = None) -> None:
        dir_path = root or os.getenv("BUDGET_POLICY_BACKEND_FS_DIR")
        self._root = Path(dir_path or Path(tempfile.gettempdir()) / "budget_policies")
        self._root.mkdir(parents=True, exist_ok=True)

    def _file_path(self, tenant_id: str, env: str) -> Path:
        name = f"{tenant_id}_{env}.policies.json"
        return self._root / name

    def _load_policies(self, tenant_id: str, env: str) -> List[BudgetPolicy]:
        path = self._file_path(tenant_id, env)
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
        policies = []
        for entry in raw:
            policies.append(BudgetPolicy(**entry))
        return policies

    def _write_policies(self, tenant_id: str, env: str, policies: List[BudgetPolicy]) -> None:
        path = self._file_path(tenant_id, env)
        with path.open("w", encoding="utf-8") as fh:
            json.dump([policy.model_dump() for policy in policies], fh, default=_json_default)

    def _match(self, a: BudgetPolicy, b: BudgetPolicy) -> bool:
        return (
            a.surface == b.surface
            and a.mode == b.mode
            and a.app == b.app
        )

    def get_policy(
        self,
        tenant_id: str,
        env: str,
        mode: str,
        surface: Optional[str] = None,
        app: Optional[str] = None,
    ) -> Optional[BudgetPolicy]:
        candidates = InMemoryBudgetPolicyRepository()._iter_candidates(tenant_id, env, mode, surface, app)
        policies = self._load_policies(tenant_id, env)
        for key in candidates:
            for policy in policies:
                candidate_key = _normalize_key(policy.tenant_id, policy.env, policy.mode, policy.surface, policy.app)
                if candidate_key == key:
                    return policy
        return None

    def save_policy(self, policy: BudgetPolicy) -> BudgetPolicy:
        policies = self._load_policies(policy.tenant_id, policy.env)
        now = datetime.now(timezone.utc)
        stored: Optional[BudgetPolicy] = None
        for index, existing in enumerate(policies):
            if self._match(existing, policy):
                stored = BudgetPolicy(
                    tenant_id=policy.tenant_id,
                    env=policy.env,
                    surface=policy.surface,
                    mode=policy.mode,
                    app=policy.app,
                    threshold=policy.threshold,
                    created_at=existing.created_at,
                    updated_at=now,
                )
                policies[index] = stored
                break
        if stored is None:
            stored = BudgetPolicy(
                tenant_id=policy.tenant_id,
                env=policy.env,
                surface=policy.surface,
                mode=policy.mode,
                app=policy.app,
                threshold=policy.threshold,
                created_at=policy.created_at,
                updated_at=now,
            )
            policies.append(stored)
        self._write_policies(policy.tenant_id, policy.env, policies)
        return stored


def _json_default(value: object) -> str:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def budget_policy_repo_from_env() -> BudgetPolicyRepository:
    backend = os.getenv("BUDGET_POLICY_BACKEND", "filesystem").lower()
    if backend == "filesystem":
        root = os.getenv("BUDGET_POLICY_BACKEND_FS_DIR")
        return FilesystemBudgetPolicyRepository(root=root)
    if backend == "inmemory":
        return InMemoryBudgetPolicyRepository()
    raise RuntimeError(
        "BUDGET_POLICY_BACKEND must be set to a durable backend (filesystem|inmemory)"
    )


_default_policy_repo: Optional[BudgetPolicyRepository] = None


def get_budget_policy_repo() -> BudgetPolicyRepository:
    """Get budget policy repository via routing registry (no env-based selection).
    
    Lane 3 wiring: Routes tabular_store resource_kind through routing registry.
    Fallback to env for backward compatibility with tests.
    """
    global _default_policy_repo
    
    if _default_policy_repo is not None:
        return _default_policy_repo
    
    # Try routing registry first (Lane 3 resolution)
    try:
        from engines.routing.registry import routing_registry
        from engines.config import runtime_config
        
        registry = routing_registry()
        route = registry.get_route(
            resource_kind="tabular_store",
            tenant_id="t_system",  # System policy applies across tenants
            env=runtime_config.env_name(),
            project_id="p_internal",
        )
        
        if route:
            backend_type = (route.backend_type or "").lower()
            if backend_type == "filesystem":
                base_dir = route.config.get("base_dir") if hasattr(route, 'config') else None
                _default_policy_repo = FilesystemBudgetPolicyRepository(root=base_dir)
                return _default_policy_repo
            # Add other backends as needed (firestore, etc.)
    except Exception as e:
        # Fallback to env if routing fails (for tests, migration)
        import logging
        logging.warning(f"Budget policy routing failed: {e}; falling back to env-based selection")
    
    # Fallback to env-based selection for backward compatibility
    _default_policy_repo = budget_policy_repo_from_env()
    return _default_policy_repo


def set_budget_policy_repo(repo: BudgetPolicyRepository) -> None:
    global _default_policy_repo
    _default_policy_repo = repo


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
