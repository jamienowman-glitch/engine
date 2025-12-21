"""Key selection abstraction backed by Google Secret Manager."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Protocol

from engines.common.secrets import SecretManagerClient, SecretManagerError, SecretNotFound
from engines.config import runtime_config
from engines.identity.models import TenantKeyConfig
from engines.identity.repository import IdentityRepository

SYSTEM_TENANT_ID = "system"

# Canonical slots
SLOT_LLM_PRIMARY = "llm_primary"
SLOT_EMBED_PRIMARY = "embed_primary"
SLOT_VECTOR_STORE_PRIMARY = "vector_store_primary"
SLOT_AUTH_JWT_SIGNING = "auth_jwt_signing"
SLOT_METRICS_PRIMARY = "metrics_primary"


class MissingKeyConfig(RuntimeError):
    def __init__(self, tenant_id: str, env: str, slot: str) -> None:
        super().__init__(f"missing key config for tenant={tenant_id}, env={env}, slot={slot}")
        self.tenant_id = tenant_id
        self.env = env
        self.slot = slot


class KeySelector(Protocol):
    def get_config(self, tenant_id: str, env: str, slot: str) -> "KeyMaterial":
        ...


@dataclass
class KeyMaterial:
    provider: str
    secret: str
    metadata: dict
    config: Optional[TenantKeyConfig]


class TenantKeySelector:
    """Resolve slot-based keys with tenant/system fallback and GSM-backed secret retrieval."""

    def __init__(
        self,
        repo: IdentityRepository,
        secret_client: Optional[SecretManagerClient] = None,
    ) -> None:
        self._repo = repo
        if secret_client:
            self._secret = secret_client
        else:
            try:
                self._secret = SecretManagerClient()
            except SecretManagerError:
                class _InMemorySecrets(SecretManagerClient):  # type: ignore
                    def __init__(self):
                        super().__init__(client=self)
                        self.storage = {}

                    def access_secret(self, secret_id: str) -> str:
                        if secret_id not in self.storage:
                            raise SecretNotFound(f"secret not found: {secret_id}")
                        return self.storage[secret_id]

                    def create_or_update_secret(self, secret_id: str, value: str) -> str:
                        self.storage[secret_id] = value
                        return secret_id

                self._secret = _InMemorySecrets()

    def get_config(self, tenant_id: str, env: str, slot: str) -> KeyMaterial:
        # Lookup order: exact -> tenant/prod -> system/env -> system/prod
        candidates = [
            (tenant_id, env, slot),
            (tenant_id, "prod", slot),
            (SYSTEM_TENANT_ID, env, slot),
            (SYSTEM_TENANT_ID, "prod", slot),
        ]
        cfg = None
        for t, e, s in candidates:
            cfg = self._repo.get_key_config(t, e, s)
            if cfg:
                break
        if not cfg:
            raise MissingKeyConfig(tenant_id, env, slot)

        secret_value: Optional[str] = None
        try:
            secret_value = self._secret.access_secret(cfg.secret_name)
        except SecretNotFound:
            if _is_local_env():
                env_fallback = os.getenv(_dev_env_var(slot))
                if env_fallback:
                    secret_value = env_fallback
            if secret_value is None:
                raise SecretNotFound(f"secret not found for slot {slot} ({cfg.secret_name})")
        except SecretManagerError as exc:  # pass through but annotate
            if _is_local_env():
                env_fallback = os.getenv(_dev_env_var(slot))
                if env_fallback:
                    secret_value = env_fallback
            if secret_value is None:
                raise SecretManagerError(f"secret access failed for slot {slot}: {exc}") from exc

        if secret_value is None:
            raise SecretNotFound(f"secret not found for slot {slot} ({cfg.secret_name})")

        return KeyMaterial(provider=cfg.provider, secret=secret_value, metadata=cfg.metadata or {}, config=cfg)


def _dev_env_var(slot: str) -> str:
    return slot.upper()


def _is_local_env() -> bool:
    env = (runtime_config.get_env() or "").lower()
    return env in {"dev", "local"}
