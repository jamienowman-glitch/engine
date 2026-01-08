from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException

from engines.common.identity import RequestContext
from engines.common.error_envelope import error_response
from engines.kill_switch.models import KillSwitch, KillSwitchUpdate
from engines.kill_switch.repository import FirestoreKillSwitchRepository, InMemoryKillSwitchRepository, KillSwitchRepository


def _default_repo() -> KillSwitchRepository:
    try:
        return FirestoreKillSwitchRepository()
    except Exception:
        return InMemoryKillSwitchRepository()


kill_switch_repo: KillSwitchRepository = _default_repo()


class KillSwitchService:
    def __init__(self, repo: Optional[KillSwitchRepository] = None) -> None:
        self.repo = repo or kill_switch_repo

    def get(self, ctx: RequestContext) -> Optional[KillSwitch]:
        return self.repo.get(ctx.tenant_id, ctx.env)

    def upsert(self, ctx: RequestContext, payload: KillSwitchUpdate) -> KillSwitch:
        existing = self.repo.get(ctx.tenant_id, ctx.env) or KillSwitch(tenant_id=ctx.tenant_id, env=ctx.env)
        if payload.disable_providers is not None:
            existing.disable_providers = [p.lower() for p in payload.disable_providers]
        if payload.disable_autonomy is not None:
            existing.disable_autonomy = payload.disable_autonomy
        if payload.disabled_actions is not None:
            existing.disabled_actions = payload.disabled_actions
        existing.updated_at = datetime.now(timezone.utc)
        return self.repo.upsert(existing)

    def ensure_provider_allowed(self, ctx: RequestContext, provider: Optional[str]) -> None:
        ks = self.repo.get(ctx.tenant_id, ctx.env)
        if not ks or not provider:
            return
        if provider.lower() in ks.disable_providers:
            error_response(
                code="kill_switch.blocked",
                message="Provider disabled by kill switch",
                status_code=403,
                gate="kill_switch",
                details={"provider": provider},
            )

    def ensure_action_allowed(self, ctx: RequestContext, action: str) -> None:
        ks = self.repo.get(ctx.tenant_id, ctx.env)
        if ks and action in ks.disabled_actions:
            error_response(
                code="kill_switch.blocked",
                message="Action disabled by kill switch",
                status_code=403,
                gate="kill_switch",
                details={"action": action},
            )

    def autonomy_allowed(self, ctx: RequestContext) -> bool:
        ks = self.repo.get(ctx.tenant_id, ctx.env)
        return not (ks and ks.disable_autonomy)


_default_service: Optional[KillSwitchService] = None


def get_kill_switch_service() -> KillSwitchService:
    global _default_service
    if _default_service is None:
        _default_service = KillSwitchService()
    return _default_service


def set_kill_switch_service(service: KillSwitchService) -> None:
    global _default_service, kill_switch_repo
    _default_service = service
    kill_switch_repo = service.repo
