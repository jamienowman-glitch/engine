"""SEO helper contracts and placeholders."""
from __future__ import annotations

from typing import List, Tuple


def plan_keywords_for_page(url: str, context: str) -> List[str]:
    """Placeholder: will call LLM later; currently returns empty list."""
    return []


def generate_slug_title_alt(title_hint: str, body: str) -> Tuple[str, str, str]:
    """Placeholder helper for slug, title, and alt text."""
    return ("", title_hint or "", "")
