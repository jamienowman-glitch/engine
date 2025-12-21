from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException

from engines.common.identity import RequestContext
from engines.firearms.models import FirearmsLicence, LicenceLevel, LicenceStatus
from engines.firearms.repository import FirearmsRepository, firearms_repo_from_env
from engines.logging.audit import emit_audit_event

DANGEROUS_ACTIONS = {
    "dangerous_tool_use": LicenceLevel.medium,
    "agent_autonomy_high": LicenceLevel.high,
    "publish_sensitive": LicenceLevel.high,
}
_LEVEL_ORDER = {LicenceLevel.low: 1, LicenceLevel.medium: 2, LicenceLevel.high: 3}


class FirearmsService:
    def __init__(self, repo: Optional[FirearmsRepository] = None) -> None:
        self.repo = repo or firearms_repo_from_env()

    def issue_licence(self, ctx: RequestContext, licence: FirearmsLicence) -> FirearmsLicence:
        licence.tenant_id = ctx.tenant_id
        licence.env = ctx.env
        issued = self.repo.issue(licence)
        emit_audit_event(ctx, action="firearms.issue", surface="firearms", metadata={"licence_id": issued.id})
        return issued

    def revoke_licence(self, ctx: RequestContext, licence_id: str) -> FirearmsLicence:
        lic = self.get_licence(ctx, licence_id)
        lic.status = LicenceStatus.revoked
        lic.updated_at = datetime.now(timezone.utc)
        updated = self.repo.update(lic)
        emit_audit_event(ctx, action="firearms.revoke", surface="firearms", metadata={"licence_id": lic.id})
        return updated

    def get_licence(self, ctx: RequestContext, licence_id: str) -> FirearmsLicence:
        lic = self.repo.get(ctx.tenant_id, ctx.env, licence_id)
        if not lic:
            raise HTTPException(status_code=404, detail="licence_not_found")
        return lic

    def list_licences(
        self,
        ctx: RequestContext,
        subject_type: Optional[str] = None,
        subject_id: Optional[str] = None,
        status: Optional[LicenceStatus] = None,
        level: Optional[LicenceLevel] = None,
    ) -> List[FirearmsLicence]:
        return self.repo.list(ctx.tenant_id, ctx.env, subject_type=subject_type, subject_id=subject_id, status=status, level=level)

    def check_licence_allowed(
        self,
        tenant_id: str,
        env: str,
        subject_type: str,
        subject_id: str,
        action: str,
    ) -> bool:
        required = DANGEROUS_ACTIONS.get(action)
        if not required:
            return True
        licences = self.repo.list(tenant_id, env, subject_type=subject_type, subject_id=subject_id, status=LicenceStatus.active)
        for lic in licences:
            if lic.expires_at and lic.expires_at < datetime.now(timezone.utc):
                continue
            lic_level = LicenceLevel(lic.level) if isinstance(lic.level, str) else lic.level
            if _LEVEL_ORDER.get(lic_level, 0) >= _LEVEL_ORDER.get(required, 0):
                return True
        return False

    def require_licence_or_raise(self, ctx: RequestContext, subject_type: str, subject_id: str, action: str) -> None:
        if not self.check_licence_allowed(ctx.tenant_id, ctx.env, subject_type, subject_id, action):
            raise HTTPException(status_code=403, detail={"error": "firearms_licence_required", "action": action})


_default_service: Optional[FirearmsService] = None


def get_firearms_service() -> FirearmsService:
    global _default_service
    if _default_service is None:
        _default_service = FirearmsService()
    return _default_service


def set_firearms_service(service: FirearmsService) -> None:
    global _default_service
    _default_service = service
