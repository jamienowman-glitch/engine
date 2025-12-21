"""Settings data models."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from engines.nexus.cards.models import Card

# Settings are primarily just Cards, but we can define explicit read models if needed.
# For now, we return Card objects directly or lists of them.

class SettingsResponse(BaseModel):
    """Container for settings response."""
    items: List[Card]
