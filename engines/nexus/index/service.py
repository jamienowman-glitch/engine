"""Card Indexing Service."""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

from engines.common.identity import RequestContext
from engines.logging.event_log import EventLogEntry, default_event_logger
from engines.nexus.cards.models import Card
from engines.nexus.index.models import SearchQuery, SearchResult
from engines.nexus.index.repository import InMemoryVectorStore, VectorStore

# Singleton store for Phase 4 (in-memory persistence within process)
_GLOBAL_STORE = InMemoryVectorStore()

class CardIndexService:
    def __init__(self, store: VectorStore | None = None):
        self.store = store or _GLOBAL_STORE
        # Mock embedding dimension
        self.dim = 16 

    def _mock_embedding(self, text: str) -> List[float]:
        """
        Deterministic mock embedding: hash terms to dimension buckets.
        This provides stable vectors for "search" without an LLM.
        """
        vec = [0.0] * self.dim
        for word in text.split():
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            idx = h % self.dim
            # Simple sign
            sign = 1 if (h % 2 == 0) else -1
            vec[idx] += sign
        
        # Normalize
        norm = sum(x*x for x in vec) ** 0.5
        if norm > 0:
            vec = [x/norm for x in vec]
        return vec

    def index_card(self, ctx: RequestContext, card: Card) -> None:
        """
        Embed and upsert card.
        """
        # Combine header and body for indexing
        text_content = f"{card.card_type} {card.body_text}"
        vector = self._mock_embedding(text_content)
        
        metadata = {
            "tenant_id": ctx.tenant_id,
            "env": ctx.env,
            "card_type": card.card_type,
            "version": card.version
        }
        
        self.store.upsert(card.card_id, vector, metadata)
        
        default_event_logger(
            EventLogEntry(
                event_type="card_indexed",
                asset_type="card",
                asset_id=card.card_id,
                tenant_id=ctx.tenant_id,
                user_id=ctx.user_id,
                metadata={"vector_dim": self.dim}
            )
        )

    def search(self, ctx: RequestContext, query: SearchQuery) -> List[SearchResult]:
        """
        Search for cards. Enforces tenant/env isolation.
        """
        vector = self._mock_embedding(query.query_text)
        
        # Enforce tenancy in filters
        filters = query.filters or {}
        filters["tenant_id"] = ctx.tenant_id
        filters["env"] = ctx.env
        
        results = self.store.search(vector, filters, query.top_k)
        
        # Log search
        default_event_logger(
            EventLogEntry(
                event_type="card_search",
                asset_type="index",
                asset_id="global_index",
                tenant_id=ctx.tenant_id,
                user_id=ctx.user_id,
                metadata={
                    "query_text_len": len(query.query_text),
                    "result_count": len(results)
                }
            )
        )
        return results
