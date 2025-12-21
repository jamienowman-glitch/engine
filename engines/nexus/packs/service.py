"""Influence Pack Service."""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from engines.common.identity import RequestContext
from engines.logging.event_log import EventLogEntry, default_event_logger
from engines.nexus.index.models import SearchQuery
from engines.nexus.index.service import CardIndexService
from engines.nexus.packs.models import CardRef, InfluencePack


class PackService:
    def __init__(self, index_service: CardIndexService | None = None):
        self.index_service = index_service or CardIndexService()

    def create_pack(self, ctx: RequestContext, query: SearchQuery) -> InfluencePack:
        """
        Create an Influence Pack by querying the index and wrapping results.
        Strictly passthrough; no interpretation.
        """
        # 1. Query Index
        # (Tenant isolation enforced by CardIndexService)
        results = self.index_service.search(ctx, query)
        
        # 2. Map to CardRefs
        card_refs = []
        for r in results:
            # We treat snippet purely as opaque debug text or omit it
            ref = CardRef(
                card_id=r.id,
                score=r.score,
                excerpt=r.snippet, # Opaque pass-through
                artifact_refs=[] # Placeholders, normally would come from Index metadata
            )
            card_refs.append(ref)
            
        # 3. Assemble Pack
        pack_id = str(uuid.uuid4())
        pack = InfluencePack(
            pack_id=pack_id,
            tenant_id=ctx.tenant_id,
            env=ctx.env,
            query=query,
            card_refs=card_refs,
            created_by=ctx.user_id,
            metadata={
                "result_count": len(card_refs)
            }
        )
        
        # 4. Log Event
        default_event_logger(
            EventLogEntry(
                event_type="pack_created",
                asset_type="influence_pack",
                asset_id=pack_id,
                tenant_id=ctx.tenant_id,
                user_id=ctx.user_id,
                metadata={
                    "query_len": len(query.query_text),
                    "card_count": len(card_refs)
                }
            )
        )
        
        return pack
