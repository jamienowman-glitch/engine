from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from engines.common.identity import RequestContext
from engines.common.error_envelope import error_response
from engines.persistence.events import emit_persistence_event
from engines.strategy_lock.models import StrategyDecision, StrategyLock, StrategyLockCreate, StrategyLockUpdate, StrategyStatus
from engines.strategy_lock.repository import StrategyLockRepository
from engines.strategy_lock.state import strategy_lock_repo, set_strategy_lock_repo
from engines.three_wise.models import ThreeWiseVerdict
from engines.three_wise.service import get_three_wise_service


class StrategyLockService:
    def __init__(self, repo: Optional[StrategyLockRepository] = None) -> None:
        self.repo = repo or strategy_lock_repo

    def create_lock(self, ctx: RequestContext, payload: StrategyLockCreate) -> StrategyLock:
        if not ctx.user_id:
            error_response(
                code="strategy_lock.user_id_required",
                message="user_id required for strategy lock creation",
                status_code=400,
                resource_kind="strategy_lock",
            )
        lock = StrategyLock(
            tenant_id=ctx.tenant_id,
            env=ctx.env,
            mode=ctx.mode,
            project_id=ctx.project_id,
            surface=payload.surface,
            scope=payload.scope,
            title=payload.title,
            description=payload.description,
            constraints=payload.constraints,
            allowed_actions=payload.allowed_actions,
            three_wise_id=payload.three_wise_id,
            created_by_user_id=ctx.user_id,
            valid_from=payload.valid_from,
            valid_until=payload.valid_until,
        )
        created = self.repo.create(ctx, lock)
        emit_persistence_event(ctx, resource="strategy_lock", action="create", record_id=created.id, version=created.version, event_type="strategy_lock")
        return created

    def list_locks(
        self,
        ctx: RequestContext,
        status: Optional[StrategyStatus] = None,
        surface: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> List[StrategyLock]:
        return self.repo.list(ctx, status=status, surface=surface, scope=scope)

    def get_lock(self, ctx: RequestContext, lock_id: str, version: Optional[int] = None) -> StrategyLock:
        lock = self.repo.get_version(ctx, lock_id, version) if version is not None else self.repo.get(ctx, lock_id)
        if not lock:
            error_response(
                code="strategy_lock.not_found",
                message="strategy lock not found",
                status_code=404,
                resource_kind="strategy_lock",
                details={"lock_id": lock_id, "version": version},
            )
        return lock

    def update_lock(self, ctx: RequestContext, lock_id: str, payload: StrategyLockUpdate) -> StrategyLock:
        lock = self.get_lock(ctx, lock_id)
        if payload.title is not None:
            lock.title = payload.title
        if payload.description is not None:
            lock.description = payload.description
        if payload.constraints is not None:
            lock.constraints = payload.constraints
        if payload.allowed_actions is not None:
            lock.allowed_actions = payload.allowed_actions
        if payload.three_wise_id is not None:
            lock.three_wise_id = payload.three_wise_id
        if payload.valid_until is not None:
            lock.valid_until = payload.valid_until
        lock.updated_at = datetime.now(timezone.utc)
        updated = self.repo.update(ctx, lock)
        emit_persistence_event(ctx, resource="strategy_lock", action="update", record_id=lock.id, version=updated.version, event_type="strategy_lock")
        return updated

    def approve_lock(self, ctx: RequestContext, lock_id: str) -> StrategyLock:
        lock = self.get_lock(ctx, lock_id)
        lock.status = StrategyStatus.approved
        lock.approved_by_user_id = ctx.user_id
        lock.updated_at = datetime.now(timezone.utc)
        updated = self.repo.update(ctx, lock)
        emit_persistence_event(ctx, resource="strategy_lock", action="approve", record_id=lock.id, version=updated.version, event_type="strategy_lock")
        return updated

    def reject_lock(self, ctx: RequestContext, lock_id: str) -> StrategyLock:
        lock = self.get_lock(ctx, lock_id)
        lock.status = StrategyStatus.rejected
        lock.approved_by_user_id = ctx.user_id
        lock.updated_at = datetime.now(timezone.utc)
        updated = self.repo.update(ctx, lock)
        emit_persistence_event(ctx, resource="strategy_lock", action="reject", record_id=lock.id, version=updated.version, event_type="strategy_lock")
        return updated

    def check_action_allowed(
        self,
        ctx: RequestContext,
        surface: Optional[str],
        action: str,
        now: Optional[datetime] = None,
    ) -> StrategyDecision:
        now = now or datetime.now(timezone.utc)
        locks = self.repo.list(ctx, status=StrategyStatus.approved, surface=surface)
        # consider surface-agnostic locks too
        locks += [l for l in self.repo.list(ctx, status=StrategyStatus.approved, surface=None) if l not in locks]
        for lock in locks:
            if lock.valid_from and lock.valid_from > now:
                continue
            if lock.valid_until and lock.valid_until < now:
                continue
            if "*" not in lock.allowed_actions and action not in lock.allowed_actions:
                continue
            tw_verdict = self._three_wise_verdict(ctx, lock)
            if lock.three_wise_id and tw_verdict != ThreeWiseVerdict.approve:
                return StrategyDecision(
                    allowed=False,
                    reason="three_wise_verdict_required",
                    lock_id=lock.id,
                    three_wise_verdict=tw_verdict.value if tw_verdict else None,
                )
            return StrategyDecision(allowed=True, lock_id=lock.id, reason=None, three_wise_verdict=tw_verdict.value if tw_verdict else None)
        return StrategyDecision(allowed=False, reason="strategy_lock_required", lock_id=None, three_wise_verdict=None)

    def require_strategy_lock_or_raise(self, ctx: RequestContext, surface: Optional[str], action: str) -> None:
        decision = self.check_action_allowed(ctx, surface, action)
        if not decision.allowed:
            details = {"action": action}
            if decision.lock_id:
                details["lock_id"] = decision.lock_id
            if decision.three_wise_verdict:
                details["three_wise_verdict"] = decision.three_wise_verdict
            error_response(
                code=decision.reason or "strategy_lock_required",
                message="Strategy lock required",
                status_code=409,
                resource_kind="strategy_lock",
                details=details,
            )

    def require_three_wise_approval_or_raise(self, ctx: RequestContext, lock_id: str) -> None:
        lock = self.get_lock(ctx, lock_id)
        verdict = self._three_wise_verdict(ctx, lock)
        if not lock.three_wise_id:
            error_response(
                code="three_wise_required",
                message="Three-wise approval required",
                status_code=409,
                resource_kind="strategy_lock",
                details={"lock_id": lock_id},
            )
        if verdict != ThreeWiseVerdict.approve:
            error_response(
                code="three_wise_verdict_required",
                message="Three-wise verdict not approved",
                status_code=409,
                resource_kind="strategy_lock",
                details={"lock_id": lock_id, "three_wise_verdict": verdict.value if verdict else None},
            )

    @staticmethod
    def _three_wise_verdict(ctx: RequestContext, lock: StrategyLock) -> Optional[ThreeWiseVerdict]:
        if not lock.three_wise_id:
            return None
        try:
            record = get_three_wise_service().get_record(ctx, lock.three_wise_id)
            return record.verdict or ThreeWiseVerdict.unsure
        except Exception:
            return None


_default_service: Optional[StrategyLockService] = None


def get_strategy_lock_service() -> StrategyLockService:
    global _default_service
    if _default_service is None:
        _default_service = StrategyLockService()
    return _default_service


def set_strategy_lock_service(service: StrategyLockService) -> None:
    global _default_service
    _default_service = service
    set_strategy_lock_repo(service.repo)
