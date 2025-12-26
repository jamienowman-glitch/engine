"""Tests for CadGanttView generation from plan_of_work engine."""
from unittest.mock import Mock

from engines.cad_viewer.service import CadViewerService, MissingArtifactError
from engines.plan_of_work.models import PlanOfWork, PlanTask, DependencyType, PlanDependency, TaskCategory


def _make_plan_task(task_id: str, name: str, duration: float, deps=None) -> PlanTask:
    """Create a PlanTask fixture."""
    deps = deps or []
    return PlanTask(
        id=task_id,
        name=name,
        description=f"Task: {name}",
        category=TaskCategory.FOUNDATION,
        duration_days=duration,
        dependencies=[
            PlanDependency(
                predecessor_task_id=dep,
                successor_task_id=task_id,
                dependency_type=DependencyType.FINISH_TO_START,
            )
            for dep in deps
        ],
        boq_refs=[],
        cost_refs=[],
    )


def _make_plan(task_count: int = 2) -> PlanOfWork:
    """Create a PlanOfWork fixture."""
    tasks = [
        _make_plan_task("task-1", "Excavate", 4.0),
        _make_plan_task("task-2", "Foundation", 4.0, deps=["task-1"]),
    ]
    if task_count > 2:
        for i in range(2, task_count):
            tasks.append(_make_plan_task(f"task-{i+1}", f"Phase {i}", 3.0, deps=[f"task-{i}"]))
    
    plan = PlanOfWork(
        id="plan-test-001",
        cost_model_id="cost-001",
        tasks=tasks,
        critical_path_duration_days=8.0,
        critical_path_task_ids=["task-1", "task-2"],
    )
    return plan


def test_build_gantt_view_success():
    """Test successful gantt view generation from plan."""
    # Create mock plan service
    plan = _make_plan(task_count=2)
    mock_plan_svc = Mock()
    mock_plan_svc.generate_plan.return_value = plan
    
    # Create service with mocked dependency
    svc = CadViewerService(plan_service=mock_plan_svc)
    
    # Build gantt view
    view = svc.build_gantt_view(
        project_id="proj-001",
        cost_model_id="cost-001",
        context={"tenant_id": "tenant-test", "env": "dev", "request_id": "req-123"},
    )
    
    # Assert view structure
    assert view.project_id == "proj-001"
    assert view.cad_model_id == "cost-001"
    assert len(view.tasks) == 2
    assert view.tasks[0].name == "Excavate"
    assert view.tasks[1].name == "Foundation"
    assert view.tasks[1].predecessors == ["task-1"]
    
    # Assert deterministic hashes
    assert view.view_hash is not None
    assert view.tasks[0].hash is not None
    assert view.tasks[1].hash is not None
    
    # Assert request context propagated
    assert view.meta.get("tenant_id") == "tenant-test"
    assert view.meta.get("env") == "dev"
    assert view.meta.get("request_id") == "req-123"


def test_build_gantt_view_missing_plan():
    """Test error when plan_of_work is missing/empty."""
    # Create mock plan service that returns None
    mock_plan_svc = Mock()
    mock_plan_svc.generate_plan.return_value = None
    
    svc = CadViewerService(plan_service=mock_plan_svc)
    
    # Should raise MissingArtifactError
    try:
        svc.build_gantt_view(project_id="proj-001", cost_model_id="cost-001")
        assert False, "Expected MissingArtifactError"
    except MissingArtifactError as e:
        assert "plan_of_work" in e.missing_kinds


def test_build_gantt_view_determinism():
    """Test that same inputs produce identical hashes."""
    plan = _make_plan(task_count=2)
    mock_plan_svc = Mock()
    mock_plan_svc.generate_plan.return_value = plan
    
    svc = CadViewerService(plan_service=mock_plan_svc)
    
    # Generate view twice with same inputs
    view1 = svc.build_gantt_view(project_id="proj-001", cost_model_id="cost-001")
    view2 = svc.build_gantt_view(project_id="proj-001", cost_model_id="cost-001")
    
    # Hashes should match
    assert view1.view_hash == view2.view_hash
    assert view1.tasks[0].hash == view2.tasks[0].hash
    assert view1.tasks[1].hash == view2.tasks[1].hash
