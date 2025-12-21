"""Service layer for tenant key slots and GSM writes."""
from __future__ import annotations

from typing import Dict, Optional

from engines.common.secrets import SecretManagerClient, SecretManagerError, canonical_secret_id
from engines.identity.models import TenantKeyConfig
from engines.identity.repository import IdentityRepository


class KeyConfigService:
    def __init__(
        self,
        repo: IdentityRepository,
        secrets: Optional[SecretManagerClient] = None,
        system_tenant: str = "system",
    ) -> None:
        self._repo = repo
        if secrets:
            self._secrets = secrets
        else:
            try:
                self._secrets = SecretManagerClient()
            except SecretManagerError:
                # Dev/test fallback when google-cloud-secretmanager is unavailable
                class _InMemorySecrets(SecretManagerClient):  # type: ignore
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

                self._secrets = _InMemorySecrets()
        self._system_tenant = system_tenant

    def list_configs(self, tenant_id: str) -> list[TenantKeyConfig]:
        return self._repo.list_key_configs(tenant_id)

    def get_config(self, tenant_id: str, env: str, slot: str) -> Optional[TenantKeyConfig]:
        return self._repo.get_key_config(tenant_id, env, slot)

    def upsert_config(
        self,
        tenant_id: str,
        env: str,
        slot: str,
        provider: str,
        secret_value: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> TenantKeyConfig:
        secret_id = canonical_secret_id(tenant_id, env, slot)
        self._secrets.create_or_update_secret(secret_id, secret_value)
        cfg = TenantKeyConfig(
            tenant_id=tenant_id,
            env=env,
            slot=slot,
            provider=provider,
            secret_name=secret_id,
            metadata=metadata or {},
        )
        return self._repo.set_key_config(cfg)
