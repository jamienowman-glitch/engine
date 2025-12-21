"""Atom Service layer."""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from fastapi import HTTPException

from engines.common.identity import RequestContext
from engines.logging.event_log import EventLogEntry, default_event_logger
from engines.nexus.atoms.models import AtomArtifact
from engines.nexus.atoms.repository import AtomRepository, InMemoryAtomRepository


class AtomService:
    def __init__(self, repo: AtomRepository | None = None):
        self.repo = repo or InMemoryAtomRepository()

    def create_atom_from_raw(
        self,
        ctx: RequestContext,
        raw_asset_id: str,
        op_type: str,
        params: Dict[str, Any] | None = None,
    ) -> AtomArtifact:
        """
        Deterministic creation of an atom from a raw asset.
        """
        # NOTE: In a real implementation, we would fetch the RawAsset here to verify existence 
        # and get its URI/content. For Phase 2, we assume it exists effectively or is passed by ref.
        # We perform a "mock" operation since we don't have heavy media libs here yet.
        
        atom_id = str(uuid.uuid4())
        params = params or {}
        
        # Deterministic Logic Placeholder
        content = None
        uri = None
        
        if op_type == "identity":
            # Pass-through logic (conceptual)
            content = "identity_content_placeholder"
        elif op_type == "mock_text_split":
            content = params.get("text_chunk", "default_chunk")
        else:
            # We allow unknown ops for testing but log them
            pass

        atom = AtomArtifact(
            atom_id=atom_id,
            tenant_id=ctx.tenant_id,
            env=ctx.env,
            parent_asset_id=raw_asset_id,
            op_type=op_type,
            op_version="v1",
            content=content,
            uri=uri,
            metadata={
                "params": params
            },
            created_by=ctx.user_id
        )
        
        saved = self.repo.create_atom(atom)

        # Log lineage
        default_event_logger(
            EventLogEntry(
                event_type="atom_created",
                asset_type="atom",
                asset_id=atom_id,
                tenant_id=ctx.tenant_id,
                user_id=ctx.user_id,
                origin_ref={
                    "parent_asset_id": raw_asset_id,
                    "op_type": op_type
                },
                metadata={
                    "op_type": op_type,
                    "parent_asset_id": raw_asset_id
                }
            )
        )

        return saved

    def get_atom(self, ctx: RequestContext, atom_id: str) -> AtomArtifact:
        atom = self.repo.get_atom(ctx.tenant_id, ctx.env, atom_id)
        if not atom:
            raise HTTPException(status_code=404, detail="Atom not found")
        return atom
