"""Simplified tests for CAD Diff functionality."""

import pytest
from datetime import datetime, timezone

from engines.cad_semantics.models import SemanticElement, SemanticModel
from engines.boq_quantities.models import BoQItem, BoQModel
from engines.plan_of_work.models import PlanTask, PlanOfWork
from engines.cad_diff.models import ChangeType, SeverityLevel
from engines.cad_diff.service import DiffService


def make_semantic_element(id_: str, sem_type: str = "wall", area: float = 50.0) -> SemanticElement:
    """Helper to create semantic elements with all required fields."""
    return SemanticElement(
        id=id_,
        cad_entity_id=f"entity_{id_}",
        semantic_type=sem_type,
        layer="A-LAYER",
        area=area,
        height=3.0,
        confidence=0.95,
        geometry_ref={"entity": f"entity_{id_}", "bounds": [0, 0, 10, area/10]},
    )


@pytest.fixture
def semantics_v1():
    """Semantic model v1 with 2 elements."""
    return SemanticModel(
        id="sem_v1",
        cad_model_id="cad_001",
        elements=[
            make_semantic_element("wall_001", "wall", 50.0),
            make_semantic_element("door_001", "door", 2.0),
        ],
    )


@pytest.fixture
def semantics_v2_added(semantics_v1):
    """Semantic model v2 with added element."""
    return SemanticModel(
        id="sem_v2",
        cad_model_id="cad_001",
        elements=semantics_v1.elements + [make_semantic_element("wall_002", "wall", 40.0)],
    )


@pytest.fixture
def semantics_v2_modified():
    """Semantic model v2 with modified area."""
    return SemanticModel(
        id="sem_v2",
        cad_model_id="cad_001",
        elements=[
            make_semantic_element("wall_001", "wall", 55.0),  # Changed from 50.0
            make_semantic_element("door_001", "door", 2.0),
        ],
    )


class TestSemanticDiffs:
    """Test semantic element diffs."""
    
    def test_element_added(self, semantics_v1, semantics_v2_added):
        """Detect added element."""
        diff = DiffService.diff_semantics(semantics_v1, semantics_v2_added)
        
        assert diff.added_count == 1
        assert diff.removed_count == 0
        assert diff.modified_count == 0
        assert len(diff.element_diffs) == 1
        assert diff.element_diffs[0].change_type == ChangeType.ADDED
    
    def test_element_modified(self, semantics_v1, semantics_v2_modified):
        """Detect modified element."""
        diff = DiffService.diff_semantics(semantics_v1, semantics_v2_modified)
        
        assert diff.added_count == 0
        assert diff.removed_count == 0
        assert diff.modified_count == 1
        assert len(diff.element_diffs) == 1
        assert diff.element_diffs[0].change_type == ChangeType.MODIFIED
    
    def test_hash_deterministic(self, semantics_v1, semantics_v2_added):
        """Hash is deterministic."""
        diff1 = DiffService.diff_semantics(semantics_v1, semantics_v2_added)
        diff2 = DiffService.diff_semantics(semantics_v1, semantics_v2_added)
        
        assert diff1.model_hash == diff2.model_hash
    
    def test_no_changes(self, semantics_v1):
        """No changes if identical."""
        v1_copy = SemanticModel(
            id="copy",
            cad_model_id=semantics_v1.cad_model_id,
            elements=semantics_v1.elements,
        )
        
        diff = DiffService.diff_semantics(semantics_v1, v1_copy)
        
        assert diff.total_changes == 0
        assert len(diff.element_diffs) == 0


class TestBoQDiffs:
    """Test BoQ diffs."""
    
    def test_quantity_delta(self):
        """Detect quantity changes."""
        v1 = BoQModel(
            id="boq_v1",
            semantic_model_id="sem",
            items=[
                BoQItem(
                    id="item_001",
                    element_type="wall",
                    quantity=50.0,
                    unit="m²",
                    scope_id="s1",
                    formula_used="wall_area",
                ),
                BoQItem(
                    id="item_002",
                    element_type="door",
                    quantity=2.0,
                    unit="count",
                    scope_id="s1",
                    formula_used="door_count",
                ),
            ],
        )
        
        v2 = BoQModel(
            id="boq_v2",
            semantic_model_id="sem",
            items=[
                BoQItem(
                    id="item_001",
                    element_type="wall",
                    quantity=55.0,  # Changed
                    unit="m²",
                    scope_id="s1",
                    formula_used="wall_area",
                ),
                BoQItem(
                    id="item_002",
                    element_type="door",
                    quantity=2.0,
                    unit="count",
                    scope_id="s1",
                    formula_used="door_count",
                ),
            ],
        )
        
        diff = DiffService.diff_boq(v1, v2)
        
        assert diff.total_changes == 1
        assert len(diff.boq_deltas) == 1
        assert diff.boq_deltas[0].boq_item_id == "item_001"
        assert diff.boq_deltas[0].quantity_delta == 5.0


class TestPlanDiffs:
    """Test plan diffs."""
    
    def test_duration_delta(self):
        """Detect task duration changes."""
        v1 = PlanOfWork(
            id="plan_v1",
            cost_model_id="cost_001",
            tasks=[
                PlanTask(
                    id="task_001",
                    name="Excavation",
                    description="Site excavation",
                    category="foundation",
                    duration_days=5.0,
                    is_critical=True,
                ),
            ],
        )
        
        v2 = PlanOfWork(
            id="plan_v2",
            cost_model_id="cost_001",
            tasks=[
                PlanTask(
                    id="task_001",
                    name="Excavation",
                    description="Site excavation",
                    category="foundation",
                    duration_days=6.0,  # Changed
                    is_critical=True,
                ),
            ],
        )
        
        diff = DiffService.diff_plan(v1, v2)
        
        assert diff.total_changes == 1
        assert len(diff.task_impacts) == 1
        assert diff.task_impacts[0].duration_delta_days == 1.0


class TestCachingAndDeterminism:
    """Test caching and determinism."""
    
    def test_cache_key_format(self):
        """Cache keys are properly formatted."""
        key = DiffService._cache_key("art1", "art2", "1.0")
        assert isinstance(key, str)
        assert len(key) == 16
        assert key.isalnum()
    
    def test_cache_key_deterministic(self):
        """Same inputs produce same cache key."""
        key1 = DiffService._cache_key("a", "b", "1.0")
        key2 = DiffService._cache_key("a", "b", "1.0")
        assert key1 == key2
    
    def test_cache_key_unique_for_different_inputs(self):
        """Different inputs produce different cache keys."""
        key1 = DiffService._cache_key("a", "b", "1.0")
        key2 = DiffService._cache_key("a", "c", "1.0")
        assert key1 != key2
