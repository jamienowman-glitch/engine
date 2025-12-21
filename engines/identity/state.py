"""Shared identity repository singleton for routes/services."""
from __future__ import annotations

import os

from engines.identity.repository import InMemoryIdentityRepository, IdentityRepository, FirestoreIdentityRepository


def _default_repo() -> IdentityRepository:
    backend = os.getenv("IDENTITY_BACKEND", "").lower()
    if backend == "firestore":
        try:
            return FirestoreIdentityRepository()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize FirestoreIdentityRepository: {e}")
    
    raise RuntimeError(f"IDENTITY_BACKEND must be 'firestore'. Got: '{backend}'")


class LazyIdentityRepo:
    def __init__(self):
        self._impl = None

    @property
    def _repo(self) -> IdentityRepository:
        if self._impl is None:
            self._impl = _default_repo()
        return self._impl

    def __getattr__(self, name):
        return getattr(self._repo, name)

identity_repo: IdentityRepository = LazyIdentityRepo()  # type: ignore

def set_identity_repo(repo: IdentityRepository) -> None:
    global identity_repo
    # Determine if we are wrapping checking proxy or actual repo
    # If we want to support switching, we should probably update the proxy's impl
    # But for tests usually we overwrite the variable.
    # However, since identity_repo is now an instance of LazyIdentityRepo, 
    # overwriting it with a real repo works for the module variable, but
    # anyone who already imported it has the old reference (the proxy).
    # So we should update the proxy's internal impl.
    if isinstance(identity_repo, LazyIdentityRepo):
        identity_repo._impl = repo
    else:
        # Should not happen unless someone manually overwrote it already
        identity_repo = repo
