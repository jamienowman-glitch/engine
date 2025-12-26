"""
Tests for strict metadata validation of `boq_quantities` artifacts.
"""

import pytest
from engines.media_v2.models import DerivedArtifact

class TestBoQValidation:
    
    def test_boq_artifact_valid(self):
        """Test creating a valid boq_quantities artifact."""
        artifact = DerivedArtifact(
            id="boq_123",
            parent_asset_id="sem_123",
            kind="boq_quantities",
            uri="boq://test",
            tenant_id="t1",
            env="dev",
            meta={
                "source_semantics_id": "sem_123",
                "calc_version": "1.0.0",
                "item_count": 100,
                "scope_count": 5,
                "model_hash": "abc1234567890def"
            }
        )
        assert artifact.id == "boq_123"
        assert artifact.kind == "boq_quantities"

    def test_boq_artifact_missing_version(self):
        """Test failure when calc_version is missing."""
        with pytest.raises(ValueError, match="boq_quantities requires meta fields: calc_version"):
            DerivedArtifact(
                id="boq_bad",
                parent_asset_id="sem_123",
                kind="boq_quantities",
                uri="boq://test",
                tenant_id="t1",
                env="dev",
                meta={
                    "source_semantics_id": "sem_123",
                    # "calc_version": "1.0.0", # Missing
                    "item_count": 100,
                    "scope_count": 5,
                    "model_hash": "abc"
                }
            )

    def test_boq_artifact_none_values(self):
        """Test failure when required fields are None."""
        with pytest.raises(ValueError, match="boq_quantities requires meta fields: model_hash"):
            DerivedArtifact(
                id="boq_none",
                parent_asset_id="sem_123",
                kind="boq_quantities",
                uri="boq://test",
                tenant_id="t1",
                env="dev",
                meta={
                    "source_semantics_id": "sem_123",
                    "calc_version": "1.0.0",
                    "item_count": 100,
                    "scope_count": 5,
                    "model_hash": None # Invalid
                }
            )
