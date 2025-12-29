"""
Tests for BoQ service registration integration.
"""

import pytest
from engines.boq_quantities.service import BoQQuantitiesService
from engines.boq_quantities.models import BoQModel
from engines.media_v2.models import DerivedArtifact

# Mock Context
class MockContext:
    tenant_id = "test_tenant"
    env = "test_env"

class TestBoQRegistration:
    
    def test_register_artifact_compliant(self):
        """Test that register_artifact produces a valid DerivedArtifact."""
        service = BoQQuantitiesService()
        model = BoQModel(
            semantic_model_id="sem_1",
            calc_version="2.0.0",
            item_count=10,
            model_hash="hash_123",
        )
        # Dummy scope to ensure scope_count > 0 validity if needed? 
        # Requirement is just presence logic not >0.
        
        # We catch any validation error here
        artifact_id = service.register_artifact("sem_1", model, "2.0.0", MockContext())
        assert artifact_id.startswith("boq_sem_1_")

    def test_register_artifact_validation_failure(self):
        """Test that missing data (like None hash) triggers validation error."""
        service = BoQQuantitiesService()
        model = BoQModel(
            semantic_model_id="sem_bad",
            calc_version="1.0.0",
            model_hash=None # Should trigger validation error
        )
        
        with pytest.raises(ValueError, match="boq_quantities requires meta fields: model_hash"):
             service.register_artifact("sem_bad", model, "1.0.0", MockContext())
