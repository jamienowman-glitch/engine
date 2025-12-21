"""Settings Facade Service."""
from __future__ import annotations

from typing import List, Optional

from engines.common.identity import RequestContext
from engines.logging.event_log import EventLogEntry, default_event_logger
from engines.nexus.cards.models import Card
from engines.nexus.cards.repository import CardRepository, InMemoryCardRepository
# Ideally we queried the INDEX service, but for exact retrieval by card_type within a tenant,
# we might want to use the repository directly if we want consistent reads, OR the index if we want search.
# The spec says "Serve tenant-configurable settings as data... via filtered reads".
# Index is better for "get all of type X". Repo is better for "get exact ID".
# Since we don't know the IDs of settings (they are created by users), we must Query by Type.
# So we use CardIndexService to find IDs, then Repo to get full content (if Index snippet isn't enough).
# Actually, CardIndexService returns SearchResult which currently lacks the full body.
# WE NEED TO FETCH FULL CARD.
# So: Index -> IDs -> Repo -> Cards.

from engines.nexus.index.models import SearchQuery
from engines.nexus.index.service import CardIndexService
from engines.nexus.cards.service import CardService

class SettingsService:
    def __init__(
        self, 
        index_service: CardIndexService | None = None,
        card_service: CardService | None = None
    ):
        self.index_service = index_service or CardIndexService()
        self.card_service = card_service or CardService()

    def _get_cards_by_type(self, ctx: RequestContext, card_type: str, limit: int = 100) -> List[Card]:
        """
        Helper: Find cards by type using Index, then fetch full content.
        """
        # 1. Search Index
        query = SearchQuery(
            query_text="", # Empty query, rely on filters
            filters={"card_type": card_type},
            top_k=limit
        )
        results = self.index_service.search(ctx, query)
        
        # 2. Fetch Full Content
        # (Naive N+1 fetch for now, assuming settings count is small per tenant)
        cards = []
        for r in results:
            try:
                card = self.card_service.get_card(ctx, r.id)
                cards.append(card)
            except Exception:
                # ignore missing cards (index drift)
                pass
        
        # Log Access
        default_event_logger(
            EventLogEntry(
                event_type="settings_read",
                asset_type="settings",
                asset_id=card_type,
                tenant_id=ctx.tenant_id,
                user_id=ctx.user_id,
                metadata={"count": len(cards)}
            )
        )
        
        return cards

    def get_surface_settings(self, ctx: RequestContext) -> Optional[Card]:
        """Get the singleton surface_settings card."""
        cards = self._get_cards_by_type(ctx, "surface_settings", limit=1)
        return cards[0] if cards else None

    def get_apps(self, ctx: RequestContext) -> List[Card]:
        """Get all app definitions."""
        return self._get_cards_by_type(ctx, "app_definition")

    def get_connectors(self, ctx: RequestContext) -> List[Card]:
        """Get all connector configs."""
        return self._get_cards_by_type(ctx, "connector_config")
