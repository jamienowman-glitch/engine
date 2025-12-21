"""Card Service."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import HTTPException

from engines.common.identity import RequestContext
from engines.logging.event_log import EventLogEntry, default_event_logger
from engines.nexus.cards.models import Card
from engines.nexus.cards.parser import parse_card_text
from engines.nexus.cards.repository import CardRepository, InMemoryCardRepository



class CardService:
    def __init__(self, repo: CardRepository | None = None, index_service = None):
        self.repo = repo or InMemoryCardRepository()
        self.index_service = index_service  # Dependency injection optional

    def create_card(self, ctx: RequestContext, text: str) -> Card:
        """
        Parses text and creates a card.
        """
        header, body = parse_card_text(text)
        
        # Validation: check required keys in header
        card_type = header.get("card_type")
        if not card_type:
            raise HTTPException(status_code=422, detail="Missing 'card_type' in YAML header")
        
        version = str(header.get("version", "v1"))
        card_id = str(uuid.uuid4())

        card = Card(
            card_id=card_id,
            tenant_id=ctx.tenant_id,
            env=ctx.env,
            version=version,
            card_type=card_type,
            header=header,
            body_text=body,
            full_text=text,
            created_by=ctx.user_id
        )
        
        saved = self.repo.create_card(card)
        
        # Log event
        default_event_logger(
            EventLogEntry(
                event_type="card_created",
                asset_type="card",
                asset_id=card_id,
                tenant_id=ctx.tenant_id,
                user_id=ctx.user_id,
                metadata={
                    "card_type": card_type,
                    "version": version
                }
            )
        )
        
        # Trigger Indexing (Local Import / Lazy Instantiation to avoid circular dep)
        if self.index_service:
            self.index_service.index_card(ctx, saved)
        else:
            # Default behavior if strictly necessary, but preferably injected
            # If not injected, we try to import locally
            from engines.nexus.index.service import CardIndexService
            CardIndexService().index_card(ctx, saved)

        return saved

    def get_card(self, ctx: RequestContext, card_id: str) -> Card:
        card = self.repo.get_card(ctx.tenant_id, ctx.env, card_id)
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")
        return card
