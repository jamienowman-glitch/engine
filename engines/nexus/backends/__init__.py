from __future__ import annotations

from typing import Any

from engines.config import runtime_config


def get_backend(client: Any = None):
    """Return a Nexus backend instance (firestore|bigquery only in prod).
    
    GAP-G3: Block noop backend and enforce durable selection.
    - Production paths must use firestore or bigquery
    - Raises error if noop or memory backend is selected
    """
    backend = (runtime_config.get_nexus_backend() or "firestore").lower()
    if backend in {"firestore"}:
        from engines.nexus.backends.firestore_backend import FirestoreNexusBackend

        return FirestoreNexusBackend(client=client)
    if backend in {"bigquery", "bq"}:
        from engines.nexus.backends.bigquery_backend import BigQueryNexusBackend

        return BigQueryNexusBackend(client=client)
    if backend in {"noop"}:
        raise RuntimeError(
            "NEXUS_BACKEND='noop' is not allowed. "
            "Production requires 'firestore' or 'bigquery'. "
            "Remove NEXUS_BACKEND env var to default to firestore."
        )
    if backend in {"memory", "in-memory"}:
        raise RuntimeError("NEXUS_BACKEND='memory' is not allowed in Real Infra mode.")
    raise RuntimeError(f"unsupported NEXUS_BACKEND={backend}")

