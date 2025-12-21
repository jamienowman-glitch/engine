"""Atom Repository."""
from __future__ import annotations

from typing import Dict, Protocol, Optional

from engines.nexus.atoms.models import AtomArtifact


class AtomRepository(Protocol):
    def create_atom(self, atom: AtomArtifact) -> AtomArtifact:
        ...

    def get_atom(self, tenant_id: str, env: str, atom_id: str) -> Optional[AtomArtifact]:
        ...


class InMemoryAtomRepository:
    def __init__(self):
        # Key: {tenant_id}:{env}:{atom_id} -> AtomArtifact
        self._store: Dict[str, AtomArtifact] = {}

    def _key(self, tenant_id: str, env: str, atom_id: str) -> str:
        return f"{tenant_id}:{env}:{atom_id}"

    def create_atom(self, atom: AtomArtifact) -> AtomArtifact:
        key = self._key(atom.tenant_id, atom.env, atom.atom_id)
        self._store[key] = atom
        return atom

    def get_atom(self, tenant_id: str, env: str, atom_id: str) -> Optional[AtomArtifact]:
        key = self._key(tenant_id, env, atom_id)
        return self._store.get(key)
