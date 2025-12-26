"""
Tests for strict validation of 'cad_semantics' artifacts in media_v2.
"""

import pytest
from engines.media_v2.models import DerivedArtifact

class TestCadSemanticsValidation:
    
    def test_create_valid_semantics_artifact(self):
        """Test creating a valid cad_semantics artifact."""
        artifact = DerivedArtifact(
            parent_asset_id="parent1",
            tenant_id="t1",
            env="dev",
            kind="cad_semantics",
            uri="s3://bucket/sem.json",
            meta={
                "model_hash": "abc1234",
                "graph_hash": "xyz789",
                "rule_version": "1.0.0",
                "element_count": 150,
                "level_count": 3
            }
        )
        assert artifact.kind == "cad_semantics"
        assert artifact.meta["model_hash"] == "abc1234"

    def test_create_invalid_semantics_artifact_missing_hash(self):
        """Test missing model_hash raises ValueError."""
        with pytest.raises(ValueError, match="cad_semantics requires meta fields"):
            DerivedArtifact(
                parent_asset_id="parent1",
                tenant_id="t1",
                env="dev",
                kind="cad_semantics",
                uri="s3://bucket/sem.json",
                meta={
                    # "model_hash": "abc1234",  <-- Missing
                    "graph_hash": "xyz789",
                    "rule_version": "1.0.0",
                    "element_count": 150,
                    "level_count": 3
                }
            )

    def test_create_invalid_semantics_artifact_missing_counts(self):
        """Test missing counts raises ValueError."""
        with pytest.raises(ValueError, match="cad_semantics requires meta fields"):
            DerivedArtifact(
                parent_asset_id="parent1",
                tenant_id="t1",
                env="dev",
                kind="cad_semantics",
                uri="s3://bucket/sem.json",
                meta={
                    "model_hash": "abc1234",
                    "graph_hash": "xyz789",
                    "rule_version": "1.0.0",
                    # Counts missing
                }
            )
