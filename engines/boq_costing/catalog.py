"""
Cost Catalog - Default rates and catalog management.

Implements:
- Default rate library for standard element types
- Catalog loading and versioning
- Currency conversion helpers
"""

from engines.boq_costing.models import Currency, CostCatalog, RateRecord


def create_default_catalog() -> CostCatalog:
    """
    Create default cost catalog with standard rates.
    
    TODO: HUMAN DECISION REQUIRED - Default currency is USD per phase doc.
    Rates are illustrative for MVP; would be sourced from actual QS database.
    """
    rates = [
        # Wall rates (per m²)
        RateRecord(element_type="wall", unit_type="m2", unit_rate=150.0, description="Wall assembly per m²"),
        
        # Slab rates (per m²)
        RateRecord(element_type="slab", unit_type="m2", unit_rate=200.0, description="Slab assembly per m²"),
        
        # Door rates (per unit)
        RateRecord(element_type="door", unit_type="count", unit_rate=800.0, description="Door unit"),
        
        # Window rates (per unit)
        RateRecord(element_type="window", unit_type="count", unit_rate=500.0, description="Window unit"),
        
        # Column rates (per unit)
        RateRecord(element_type="column", unit_type="count", unit_rate=1200.0, description="Column unit"),
        
        # Room rates (per m²)
        RateRecord(element_type="room", unit_type="m2", unit_rate=100.0, description="Room finishing per m²"),
        
        # Stair rates (per unit)
        RateRecord(element_type="stair", unit_type="count", unit_rate=5000.0, description="Stair unit"),
        
        # Unknown/other (per item)
        RateRecord(element_type="unknown", unit_type="count", unit_rate=100.0, description="Default unknown item"),
    ]
    
    # FX rates relative to USD (illustrative)
    fx_rates = {
        "GBP/USD": 1.27,
        "EUR/USD": 1.10,
        "CAD/USD": 0.74,
        "AUD/USD": 0.67,
        "JPY/USD": 0.0067,
    }
    
    catalog = CostCatalog(
        version="1.0.0",
        currency=Currency.USD,
        rates=rates,
        fx_rates=fx_rates,
        markup_pct=0.0,  # No markup by default
        tax_pct=0.0,  # No tax by default
        meta={
            "source": "default_catalog",
            "description": "Default MVP cost catalog (USD-based)",
            "notes": "Rates are illustrative; actual rates should come from project QS database",
        },
    )
    
    return catalog


def apply_markup_and_tax(
    amount: float,
    markup_pct: float = 0.0,
    tax_pct: float = 0.0,
) -> tuple[float, float, float]:
    """
    Apply markup and tax to amount.
    
    Returns: (marked_up_amount, tax_amount, total)
    """
    marked_up = amount * (1.0 + markup_pct / 100.0)
    tax = marked_up * (tax_pct / 100.0)
    total = marked_up + tax
    
    return marked_up, tax, total
