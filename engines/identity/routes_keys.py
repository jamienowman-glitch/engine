from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext, assert_context_matches, get_request_context
from engines.identity.key_service import KeyConfigService
from engines.identity.state import identity_repo
from engines.identity.auth import get_auth_context, require_tenant_role
from engines.common.secrets import SecretManagerClient, SecretManagerError
from engines.logging.audit import emit_audit_event
from engines.common.error_envelope import error_response
from engines.nexus.hardening.gate_chain import get_gate_chain

router = APIRouter(prefix="/tenants")

class _InMemorySecrets(SecretManagerClient):
    def __init__(self):
        super().__init__(client=self)
        self.storage = {}

    def access_secret(self, secret_id: str) -> str:
        if secret_id not in self.storage:
            raise SecretManagerError(f"secret not found: {secret_id}")
        return self.storage[secret_id]

    def create_or_update_secret(self, secret_id: str, value: str) -> str:
        self.storage[secret_id] = value
        return secret_id


def _default_service() -> KeyConfigService:
    try:
        return KeyConfigService(repo=identity_repo)
    except Exception:
        # Fall back to in-memory secrets when GSM is unavailable (dev/test)
        return KeyConfigService(repo=identity_repo, secrets=_InMemorySecrets())


_svc = _default_service()


class KeySlotUpsert(BaseModel):
    slot: str = Field(..., min_length=1)
    env: str
    provider: str
    secret_value: str
    metadata: Optional[dict] = Field(default_factory=dict)


class KeySlotResponse(BaseModel):
    tenant_id: str
    env: str
    slot: str
    provider: str
    secret_name: str
    metadata: dict
    updated_at: Optional[str] = None


def _to_response(cfg) -> KeySlotResponse:
    return KeySlotResponse(
        tenant_id=cfg.tenant_id,
        env=cfg.env,
        slot=cfg.slot,
        provider=cfg.provider,
        secret_name=cfg.secret_name,
        metadata=cfg.metadata,
        updated_at=(getattr(cfg, "updated_at", None).isoformat() if getattr(cfg, "updated_at", None) else None),
    )


@router.get("/{tenant_id}/keys", response_model=list[KeySlotResponse])
def list_key_slots(
    tenant_id: str = Path(...),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    assert_context_matches(context, tenant_id, context.env)
    require_tenant_role(auth, tenant_id, ["owner", "admin"])
    try:
        configs = _svc.list_configs(tenant_id)
        return [_to_response(cfg) for cfg in configs]
    except Exception as e:
        error_response(
            code="keys.list_error",
            message=str(e),
            status_code=500,
            resource_kind="keys"
        )


@router.get("/{tenant_id}/keys/{slot}", response_model=KeySlotResponse)
def get_key_slot(
    tenant_id: str = Path(...),
    slot: str = Path(...),
    env: Optional[str] = Query(default=None),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    env_value = env or context.env
    assert_context_matches(context, tenant_id, env_value)
    require_tenant_role(auth, tenant_id, ["owner", "admin"])
    try:
        cfg = _svc.get_config(tenant_id, env_value, slot)
        if not cfg:
            error_response(
                code="keys.not_found",
                message="key slot not found",
                status_code=404,
                resource_kind="keys",
                details={"slot": slot}
            )
        return _to_response(cfg)
    except HTTPException:
        raise
    except Exception as e:
        error_response(
            code="keys.get_error",
            message=str(e),
            status_code=500,
            resource_kind="keys"
        )


@router.put("/{tenant_id}/keys/{slot}", response_model=KeySlotResponse)
def put_key_slot(
    tenant_id: str = Path(...),
    slot: str = Path(...),
    payload: KeySlotUpsert = Body(...),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    if slot != payload.slot:
        error_response(
            code="keys.validation_error",
            message="slot path/body mismatch",
            status_code=400,
            resource_kind="keys"
        )
    assert_context_matches(context, tenant_id, payload.env)
    require_tenant_role(auth, tenant_id, ["owner", "admin"])

    # GateChain Check
    get_gate_chain().run(
        ctx=context,
        action="keys.upsert",
        surface="keys",
        subject_type="key_slot",
        subject_id=slot
    )

    try:
        cfg = _svc.upsert_config(
            tenant_id=tenant_id,
            env=payload.env,
            slot=payload.slot,
            provider=payload.provider,
            secret_value=payload.secret_value,
            metadata=payload.metadata or {},
        )
        emit_audit_event(context, action="keys.upsert", surface="keys", metadata={"slot": payload.slot, "env": payload.env})
        return _to_response(cfg)
    except Exception as e:
        error_response(
            code="keys.upsert_error",
            message=str(e),
            status_code=500,
            resource_kind="keys"
        )


# POST alias for creating slots
@router.post("/{tenant_id}/keys", response_model=KeySlotResponse)
def create_key_slot(
    tenant_id: str = Path(...),
    payload: KeySlotUpsert = Body(...),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    assert_context_matches(context, tenant_id, payload.env)
    require_tenant_role(auth, tenant_id, ["owner", "admin"])

    # GateChain Check
    get_gate_chain().run(
        ctx=context,
        action="keys.upsert",
        surface="keys",
        subject_type="key_slot",
        subject_id=payload.slot
    )

    try:
        cfg = _svc.upsert_config(
            tenant_id=tenant_id,
            env=payload.env,
            slot=payload.slot,
            provider=payload.provider,
            secret_value=payload.secret_value,
            metadata=payload.metadata or {},
        )
        return _to_response(cfg)
    except Exception as e:
        error_response(
            code="keys.upsert_error",
            message=str(e),
            status_code=500,
            resource_kind="keys"
        )


def set_key_service(service: KeyConfigService) -> None:
    global _svc
    _svc = service
