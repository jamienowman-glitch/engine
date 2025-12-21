"""Google Secret Manager helper with basic error mapping."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from engines.config import runtime_config

try:  # pragma: no cover - optional dependency in some envs
    from google.cloud import secretmanager  # type: ignore
except Exception:  # pragma: no cover
    secretmanager = None  # type: ignore


class SecretManagerError(RuntimeError):
    pass


class SecretNotFound(SecretManagerError):
    pass


class SecretAccessDenied(SecretManagerError):
    pass


@dataclass
class SecretManagerClient:
    """Thin wrapper around GSM; can be swapped in tests."""

    client: Optional[object] = None

    def __post_init__(self) -> None:
        if self.client is None:
            self.client = self._default_client()

    def _default_client(self):
        if secretmanager is None:
            raise SecretManagerError("google-cloud-secretmanager is not installed")
        project = runtime_config.get_firestore_project()
        if not project:
            raise SecretManagerError("GCP_PROJECT_ID/GCP_PROJECT missing for Secret Manager")
        return secretmanager.SecretManagerServiceClient()

    def _secret_path(self, secret_id: str) -> str:
        project = runtime_config.get_firestore_project()
        if secretmanager is None:
            raise SecretManagerError("google-cloud-secretmanager is not installed")
        return self.client.secret_path(project, secret_id)  # type: ignore[arg-type]

    def access_secret(self, secret_id: str) -> str:
        """Return the latest secret payload for the given secret id."""
        try:
            name = f"{self._secret_path(secret_id)}/versions/latest"
            response = self.client.access_secret_version(request={"name": name})  # type: ignore[arg-type]
            payload = response.payload.data.decode("UTF-8")  # type: ignore[attr-defined]
            return payload
        except Exception as exc:  # pragma: no cover - relies on GSM in CI
            msg = str(exc).lower()
            if "not found" in msg:
                raise SecretNotFound(secret_id)
            if "permission" in msg or "denied" in msg:
                raise SecretAccessDenied(secret_id)
            raise SecretManagerError(str(exc)) from exc

    def create_or_update_secret(self, secret_id: str, value: str) -> str:
        """Create a secret if missing, then add a new version with the value. Returns secret id."""
        if secretmanager is None:
            raise SecretManagerError("google-cloud-secretmanager is not installed")
        project = runtime_config.get_firestore_project()
        if not project:
            raise SecretManagerError("GCP_PROJECT_ID/GCP_PROJECT missing for Secret Manager")
        secret_path = self._secret_path(secret_id)
        try:
            self.client.get_secret(request={"name": secret_path})  # type: ignore[arg-type]
        except Exception:
            parent = f"projects/{project}"
            self.client.create_secret(  # type: ignore[attr-defined]
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
        # Add a new version
        self.client.add_secret_version(  # type: ignore[attr-defined]
            request={"parent": secret_path, "payload": {"data": value.encode("UTF-8")}}
        )
        return secret_id


def canonical_secret_id(tenant_id: str, env: str, slot: str) -> str:
    """Build a GSM-safe secret id from tenant/env/slot (slash-safe, human-readable)."""
    parts = ["tenants", tenant_id, "env", env, "slot", slot]
    return "-".join(p.replace("/", "-") for p in parts)
