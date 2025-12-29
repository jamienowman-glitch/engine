"""
Tests for strict validation of media_v2 artifacts.
"""

import pytest
from pydantic import ValidationError
from engines.media_v2.models import DerivedArtifact

class TestStrictValidation:
    """Test strict metadata validation rules."""

    def test_cad_model_valid(self):
        """Test accepting a valid cad_model artifact."""
        artifact = DerivedArtifact(
            parent_asset_id="asset123",
            tenant_id="tenant1",
            env="dev",
            kind="cad_model",
            uri="cad://123",
            meta={
                "format": "dxf",
                "units": "mm",
                "tolerance_used": 0.001,
                "adapter_version": "1.0.0",
                "source_sha256": "abc123hash",
                "extra_field": "ok"
            }
        )
        assert artifact.kind == "cad_model"
        assert artifact.meta["units"] == "mm"

    def test_cad_model_missing_fields(self):
        """Test rejecting cad_model with missing fields."""
        # Missing all required
        with pytest.raises(ValueError, match="cad_model requires meta fields"):
            DerivedArtifact(
                parent_asset_id="asset123",
                tenant_id="tenant1",
                env="dev",
                kind="cad_model",
                uri="cad://123",
                meta={}
            )
            
        # Missing just one (format)
        with pytest.raises(ValueError, match="format"):
            DerivedArtifact(
                parent_asset_id="asset123",
                tenant_id="tenant1",
                env="dev",
                kind="cad_model",
                uri="cad://123",
                meta={
                    # "format": "dxf",  <-- missing
                    "units": "mm",
                    "tolerance_used": 0.001,
                    "adapter_version": "1.0.0",
                    "source_sha256": "abc123hash",
                }
            )

    def test_cad_model_missing_context(self):
        """Test rejecting missing tenant/env (base class rule)."""
        with pytest.raises(ValueError):
            DerivedArtifact(
                parent_asset_id="asset123",
                # tenant_id missing
                env="dev",
                kind="cad_model",
                uri="cad://123",
                meta={
                    "format": "dxf",
                    "units": "mm",
                    "tolerance_used": 0.001,
                    "adapter_version": "1.0.0",
                    "source_sha256": "abc123hash",
                }
            )

    def test_other_kinds_unaffected(self):
        """Test that other kinds are not affected by cad_model rules."""
        # 'render' usually has no strict requirements in baseline
        artifact = DerivedArtifact(
            parent_asset_id="asset123",
            tenant_id="tenant1",
            env="dev",
            kind="render",
            uri="s3://foo/bar.mp4",
            meta={}
        )
        assert artifact.kind == "render"
