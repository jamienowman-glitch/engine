from __future__ import annotations

from typing import Any

from engines.config import runtime_config


def get_backend(client: Any = None):
    """Return a Nexus backend instance (Firestore only; no fallbacks)."""
    backend = (runtime_config.get_nexus_backend() or "firestore").lower()
    if backend != "firestore":
        raise RuntimeError("NEXUS_BACKEND must be 'firestore'; no memory fallback allowed")
    from engines.nexus.backends.firestore_backend import FirestoreNexusBackend

    return FirestoreNexusBackend(client=client)
