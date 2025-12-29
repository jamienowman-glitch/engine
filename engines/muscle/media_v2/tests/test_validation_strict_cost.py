"""
Tests for strict cost model metadata validation in media_v2.
"""

import pytest
from engines.media_v2.models import DerivedArtifact, ArtifactKind

def test_cost_artifact_compliant():
    """Test creating a valid cost_model artifact."""
    artifact = DerivedArtifact(
        parent_asset_id="asset_123",
        tenant_id="t1",
        env="dev",
        kind="cost_model",
        uri="cost://123",
        meta={
            "total_cost": 1500.0,
            "currency": "GBP",
            "item_count": 10,
            "model_hash": "hash123",
            "catalog_version": "1.0.0",
            "base_currency": "USD",
            "total_cost_base": 1200.0
        }
    )
    assert artifact.kind == "cost_model"
    assert artifact.meta["total_cost"] == 1500.0

def test_cost_artifact_missing_field():
    """Test failure when required field is missing."""
    with pytest.raises(ValueError, match="cost_model requires meta fields: total_cost"):
        DerivedArtifact(
            parent_asset_id="asset_123",
            tenant_id="t1",
            env="dev",
            kind="cost_model",
            uri="cost://123",
            meta={
                # Missing total_cost
                "currency": "GBP",
                "item_count": 10,
                "model_hash": "hash123",
                "catalog_version": "1.0.0",
                "base_currency": "USD",
                "total_cost_base": 1200.0
            }
        )

def test_cost_artifact_none_field():
    """Test failure when field is None."""
    with pytest.raises(ValueError, match="cost_model requires meta fields: currency"):
        DerivedArtifact(
            parent_asset_id="asset_123",
            tenant_id="t1",
            env="dev",
            kind="cost_model",
            uri="cost://123",
            meta={
                "total_cost": 1500.0,
                "currency": None, # Invalid
                "item_count": 10,
                "model_hash": "hash123",
                "catalog_version": "1.0.0",
                "base_currency": "USD",
                "total_cost_base": 1200.0
            }
        )
