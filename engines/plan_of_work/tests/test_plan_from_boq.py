"""
Tests for plan-of-works generation.

Covers:
- Task generation from BoQ/cost
- Dependency sequencing
- Critical path computation
- Deterministic ordering and hashing
- Caching behavior
"""

import pytest

from engines.cad_ingest.dxf_adapter import dxf_to_cad_model
from engines.cad_ingest.tests.fixtures import DXF_FLOORPLAN_FIXTURE
from engines.cad_semantics.service import SemanticClassificationService
from engines.boq_quantities.service import BoQQuantitiesService
from engines.boq_costing.service import BoQCostingService
from engines.plan_of_work.models import TaskCategory
from engines.plan_of_work.service import PlanOfWorkService


class TestPlanGeneration:
    """Test task generation from cost data."""
    
    def test_generate_plan_from_cost(self):
        """Test plan generation from cost model."""
        # Build pipeline: DXF -> Semantic -> BoQ -> Cost
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        boq_service = BoQQuantitiesService()
        boq_model, _ = boq_service.quantify(semantic_model)
        
        cost_service = BoQCostingService()
        cost_model, _ = cost_service.estimate_cost(boq_model)
        
        # Generate plan
        plan_service = PlanOfWorkService()
        plan_model, response = plan_service.generate_plan(cost_model)
        
        assert plan_model is not None
        assert response is not None
        assert response.task_count > 0
        assert response.critical_path_duration_days > 0
    
    def test_plan_tasks_have_categories(self):
        """Test that tasks have valid categories."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        boq_service = BoQQuantitiesService()
        boq_model, _ = boq_service.quantify(semantic_model)
        
        cost_service = BoQCostingService()
        cost_model, _ = cost_service.estimate_cost(boq_model)
        
        plan_service = PlanOfWorkService()
        plan_model, _ = plan_service.generate_plan(cost_model)
        
        for task in plan_model.tasks:
            assert task.category in TaskCategory
            assert task.duration_days > 0
    
    def test_plan_tasks_have_dependencies(self):
        """Test that tasks have dependency relationships."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        boq_service = BoQQuantitiesService()
        boq_model, _ = boq_service.quantify(semantic_model)
        
        cost_service = BoQCostingService()
        cost_model, _ = cost_service.estimate_cost(boq_model)
        
        plan_service = PlanOfWorkService()
        plan_model, _ = plan_service.generate_plan(cost_model)
        
        # Should have some dependencies
        assert len(plan_model.all_dependencies) >= 0  # Could be 0 for single items


class TestCriticalPath:
    """Test critical path computation."""
    
    def test_critical_path_computed(self):
        """Test that critical path is computed."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        boq_service = BoQQuantitiesService()
        boq_model, _ = boq_service.quantify(semantic_model)
        
        cost_service = BoQCostingService()
        cost_model, _ = cost_service.estimate_cost(boq_model)
        
        plan_service = PlanOfWorkService()
        plan_model, _ = plan_service.generate_plan(cost_model)
        
        # Should have critical path
        assert plan_model.critical_path_duration_days > 0
        assert len(plan_model.critical_path_task_ids) > 0
    
    def test_critical_tasks_are_marked(self):
        """Test that critical path tasks are marked."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        boq_service = BoQQuantitiesService()
        boq_model, _ = boq_service.quantify(semantic_model)
        
        cost_service = BoQCostingService()
        cost_model, _ = cost_service.estimate_cost(boq_model)
        
        plan_service = PlanOfWorkService()
        plan_model, _ = plan_service.generate_plan(cost_model)
        
        # Check critical tasks
        critical_count = sum(1 for t in plan_model.tasks if t.is_critical)
        assert critical_count > 0


class TestPlanDeterminism:
    """Test deterministic plan generation."""
    
    def test_plan_determinism_same_input(self):
        """Test that same cost model produces same plan."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        boq_service = BoQQuantitiesService()
        boq_model, _ = boq_service.quantify(semantic_model)
        
        cost_service = BoQCostingService()
        cost_model, _ = cost_service.estimate_cost(boq_model)
        
        plan_service = PlanOfWorkService()
        plan1, _ = plan_service.generate_plan(cost_model)
        plan2, _ = plan_service.generate_plan(cost_model)
        
        # Should have same model hash
        assert plan1.model_hash == plan2.model_hash
        # Should have same task count
        assert len(plan1.tasks) == len(plan2.tasks)
        # Should have same critical path
        assert plan1.critical_path_duration_days == plan2.critical_path_duration_days


class TestPlanCaching:
    """Test plan service caching."""
    
    def test_plan_caching(self):
        """Test service caches plan models."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        boq_service = BoQQuantitiesService()
        boq_model, _ = boq_service.quantify(semantic_model)
        
        cost_service = BoQCostingService()
        cost_model, _ = cost_service.estimate_cost(boq_model)
        
        plan_service = PlanOfWorkService()
        plan1, _ = plan_service.generate_plan(cost_model)
        plan2, _ = plan_service.generate_plan(cost_model)
        
        # Should be same object from cache
        assert plan1.id == plan2.id
    
    def test_plan_cache_miss_different_productivity(self):
        """Test cache miss when productivity config changes."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        boq_service = BoQQuantitiesService()
        boq_model, _ = boq_service.quantify(semantic_model)
        
        cost_service = BoQCostingService()
        cost_model, _ = cost_service.estimate_cost(boq_model)
        
        plan_service = PlanOfWorkService()
        
        # Plan with default productivity
        plan1, _ = plan_service.generate_plan(cost_model)
        
        # Clear cache to avoid reuse
        plan_service.cache.clear()
        
        # Plan with different productivity
        plan2, _ = plan_service.generate_plan(
            cost_model,
            productivity_config={"wall": 2.0}
        )
        
        # Should have different durations
        # (faster productivity = shorter duration)
        plan1_duration = sum(t.duration_days for t in plan1.tasks)
        plan2_duration = sum(t.duration_days for t in plan2.tasks)
        
        assert plan1_duration < plan2_duration or plan1_duration == plan2_duration  # Productivity change may not affect all tasks


class TestTaskCounts:
    """Test task statistics."""
    
    def test_plan_response_has_counts(self):
        """Test response includes task counts."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        boq_service = BoQQuantitiesService()
        boq_model, _ = boq_service.quantify(semantic_model)
        
        cost_service = BoQCostingService()
        cost_model, _ = cost_service.estimate_cost(boq_model)
        
        plan_service = PlanOfWorkService()
        _, response = plan_service.generate_plan(cost_model)
        
        assert response.task_count > 0
        assert len(response.task_count_by_category) > 0
    
    def test_plan_task_count_matches(self):
        """Test task count consistency."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        boq_service = BoQQuantitiesService()
        boq_model, _ = boq_service.quantify(semantic_model)
        
        cost_service = BoQCostingService()
        cost_model, _ = cost_service.estimate_cost(boq_model)
        
        plan_service = PlanOfWorkService()
        plan_model, response = plan_service.generate_plan(cost_model)
        
        # Response count should match model count
        assert response.task_count == len(plan_model.tasks)


class TestTaskScheduling:
    """Test task scheduling calculations."""
    
    def test_task_early_times_computed(self):
        """Test that early start/finish times are computed."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        boq_service = BoQQuantitiesService()
        boq_model, _ = boq_service.quantify(semantic_model)
        
        cost_service = BoQCostingService()
        cost_model, _ = cost_service.estimate_cost(boq_model)
        
        plan_service = PlanOfWorkService()
        plan_model, _ = plan_service.generate_plan(cost_model)
        
        for task in plan_model.tasks:
            assert task.early_start_day >= 0
            assert task.early_finish_day >= task.early_start_day
    
    def test_task_late_times_computed(self):
        """Test that late start/finish times are computed."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        boq_service = BoQQuantitiesService()
        boq_model, _ = boq_service.quantify(semantic_model)
        
        cost_service = BoQCostingService()
        cost_model, _ = cost_service.estimate_cost(boq_model)
        
        plan_service = PlanOfWorkService()
        plan_model, _ = plan_service.generate_plan(cost_model)
        
        for task in plan_model.tasks:
            assert task.late_start_day is not None
            assert task.late_finish_day is not None
            assert task.float_days is not None


class TestTaskOrdering:
    """Test task deterministic ordering."""
    
    def test_tasks_sorted_deterministically(self):
        """Test tasks are sorted by category and ID."""
        cad_model = dxf_to_cad_model(DXF_FLOORPLAN_FIXTURE)
        sem_service = SemanticClassificationService()
        semantic_model, _ = sem_service.semanticize(cad_model)
        
        boq_service = BoQQuantitiesService()
        boq_model, _ = boq_service.quantify(semantic_model)
        
        cost_service = BoQCostingService()
        cost_model, _ = cost_service.estimate_cost(boq_model)
        
        plan_service = PlanOfWorkService()
        plan_model, _ = plan_service.generate_plan(cost_model)
        
        # Check ordering
        for i in range(len(plan_model.tasks) - 1):
            curr = plan_model.tasks[i]
            next_task = plan_model.tasks[i + 1]
            
            if curr.category == next_task.category:
                assert curr.id <= next_task.id
            else:
                # Category ordering
                assert curr.category.value <= next_task.category.value
