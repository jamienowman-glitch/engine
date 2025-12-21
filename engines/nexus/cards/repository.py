"""Card Repository."""
from __future__ import annotations

from typing import Dict, Protocol, Optional, List

from engines.nexus.cards.models import Card


class CardRepository(Protocol):
    def create_card(self, card: Card) -> Card:
        ...

    def get_card(self, tenant_id: str, env: str, card_id: str) -> Optional[Card]:
        ...


class InMemoryCardRepository:
    def __init__(self):
        # Key: {tenant_id}:{env}:{card_id}
        self._store: Dict[str, Card] = {}

    def _key(self, tenant_id: str, env: str, card_id: str) -> str:
        return f"{tenant_id}:{env}:{card_id}"

    def create_card(self, card: Card) -> Card:
        key = self._key(card.tenant_id, card.env, card.card_id)
        self._store[key] = card
        return card

    def get_card(self, tenant_id: str, env: str, card_id: str) -> Optional[Card]:
        key = self._key(tenant_id, env, card_id)
        return self._store.get(key)
