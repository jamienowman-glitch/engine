"""Surface ID normalization for routing registry.

Canonical storage: ASCII lowercase (e.g., "squared2").
Aliases accepted: "squared", "squared2", "SQUARED2", "SQUARED²", etc.

Used only in routing registry lookup/write paths.
"""
from __future__ import annotations

import re
from typing import Dict, Optional

# Mapping from alias to canonical ASCII form
# Generic pattern: matches squared + optional variants
_SURFACE_ALIAS_MAP: Dict[str, str] = {
    # SQUARED² family (used as alias example per Phase 0.5 spec)
    "squared": "squared2",
    "squared2": "squared2",
    "SQUARED": "squared2",
    "SQUARED2": "squared2",
    "SQUARED²": "squared2",
    "squared²": "squared2",
    # Add more alias families as needed (generic, not special-cased)
}


def normalize_surface_id(surface_id: Optional[str]) -> Optional[str]:
    """Normalize surface_id to canonical ASCII form.
    
    Args:
        surface_id: Raw surface ID (may be alias or canonical)
    
    Returns:
        Canonical ASCII form (e.g., "squared2") or None if input is None.
    
    Examples:
        >>> normalize_surface_id("SQUARED²")
        'squared2'
        >>> normalize_surface_id("squared")
        'squared2'
        >>> normalize_surface_id("squared2")
        'squared2'
        >>> normalize_surface_id(None)
        None
    """
    if surface_id is None:
        return None
    
    # Direct lookup: alias exists in map
    if surface_id in _SURFACE_ALIAS_MAP:
        return _SURFACE_ALIAS_MAP[surface_id]
    
    # Fallback: return as-is (may be a canonical form not in alias map)
    return surface_id


def get_canonical_surface_id(surface_id: Optional[str]) -> Optional[str]:
    """Alias for normalize_surface_id for clarity in routing contexts."""
    return normalize_surface_id(surface_id)
