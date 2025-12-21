from __future__ import annotations

from typing import Any

from engines.config import runtime_config


def get_backend(client: Any = None):
    """Return a Nexus backend instance (firestore|bigquery|noop)."""
    backend = (runtime_config.get_nexus_backend() or "firestore").lower()
    if backend in {"firestore"}:
        from engines.nexus.backends.firestore_backend import FirestoreNexusBackend

        return FirestoreNexusBackend(client=client)
    if backend in {"bigquery", "bq"}:
        from engines.nexus.backends.bigquery_backend import BigQueryNexusBackend

        return BigQueryNexusBackend(client=client)
    if backend in {"noop"}:
        from engines.nexus.backends.noop_backend import NoopNexusBackend

        return NoopNexusBackend()
    if backend in {"memory", "in-memory"}:
        raise RuntimeError("NEXUS_BACKEND='memory' is not allowed in Real Infra mode.")
    raise RuntimeError(f"unsupported NEXUS_BACKEND={backend}")
