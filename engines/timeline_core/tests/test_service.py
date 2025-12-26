"""
Tests for Timeline Service.
"""

import pytest
from datetime import datetime, timedelta, timezone
from engines.timeline_core.models import Task, TaskStatus, ContentPlanItem, ContentPlanPayload
from engines.timeline_core.service import TimelineService
from engines.plan_of_work.models import PlanOfWork, PlanTask, PlanDependency, TaskCategory
from engines.boq_quantities.models import BoQModel, BoQItem, UnitType, FormulaType, Scope

class TestTimelineService:
    
    @pytest.fixture
    def service(self):
        return TimelineService()
    
    @pytest.fixture
    def ctx_a(self):
        return {"tenant_id": "tenant_a", "env": "dev"}

    @pytest.fixture
    def ctx_b(self):
        return {"tenant_id": "tenant_b", "env": "dev"}

    def create_task(self, tid, title, ctx):
        return Task(
            id=tid,
            tenant_id=ctx["tenant_id"],
            env=ctx["env"],
            request_id="req",
            title=title,
            start_ts=datetime.now(timezone.utc)
        )

    def test_crud_isolation(self, service, ctx_a, ctx_b):
        """Test that A cannot see B's tasks."""
        t1 = self.create_task("t1", "Task A", ctx_a)
        t2 = self.create_task("t2", "Task B", ctx_b)
        
        service.create_task(ctx_a, t1)
        service.create_task(ctx_b, t2)
        
        # A should see t1 only
        tasks_a = service.list_tasks(ctx_a)
        assert len(tasks_a) == 1
        assert tasks_a[0].id == "t1"
        
        # A cannot get t2
        assert service.get_task(ctx_a, "t2") is None
        
        # B sees t2
        tasks_b = service.list_tasks(ctx_b)
        assert len(tasks_b) == 1
        assert tasks_b[0].id == "t2"

    def test_cycle_detection(self, service, ctx_a):
        """Test preventing cycles."""
        t1 = self.create_task("t1", "1", ctx_a)
        t2 = self.create_task("t2", "2", ctx_a)
        t3 = self.create_task("t3", "3", ctx_a)
        
        service.create_task(ctx_a, t1)
        service.create_task(ctx_a, t2)
        service.create_task(ctx_a, t3)
        
        # 1 -> 2 -> 3
        service.add_dependency(ctx_a, "t1", "t2")
        service.add_dependency(ctx_a, "t2", "t3")
        
        # Try 3 -> 1 (Cycle!)
        with pytest.raises(ValueError, match="Cycle detected"):
            service.add_dependency(ctx_a, "t3", "t1")

    def test_topological_sort(self, service, ctx_a):
        """Test topo sort correctness."""
        # Setup: A -> B, A -> C, B -> D, C -> D
        # Order should obey dependencies.
        tasks = ["A", "B", "C", "D"]
        for t in tasks:
            service.create_task(ctx_a, self.create_task(t, t, ctx_a))
            
        service.add_dependency(ctx_a, "A", "B")
        service.add_dependency(ctx_a, "A", "C")
        service.add_dependency(ctx_a, "B", "D")
        service.add_dependency(ctx_a, "C", "D")
        
        sorted_tasks = service.topological_sort(ctx_a)
        ids = [t.id for t in sorted_tasks]
        
        # Constraints
        assert ids.index("A") < ids.index("B")
        assert ids.index("A") < ids.index("C")
        assert ids.index("B") < ids.index("D")
        assert ids.index("C") < ids.index("D")
        
    def test_filtering(self, service, ctx_a):
        """Test tag filtering."""
        t1 = self.create_task("t1", "1", ctx_a)
        t1.tags = ["engineering", "backend"]
        t2 = self.create_task("t2", "2", ctx_a)
        t2.tags = ["design"]
        
        service.create_task(ctx_a, t1)
        service.create_task(ctx_a, t2)
        
        # Filter for engineering
        res = service.list_tasks(ctx_a, filters={"tags": ["engineering"]})
        assert len(res) == 1
        assert res[0].id == "t1"
        
        # Filter for none (match all?) no, subset match logic in service
        # If I request tags=["engineering"], t2 (design) fails.
    def test_import_plan_of_work(self, service, ctx_a):
        """Test importing generic plan of work."""
        now = datetime.now(timezone.utc)
        
        # Mock Plan
        p_task1 = PlanTask(
            id="pt1", name="Dig", category=TaskCategory.FOUNDATION,
            duration_days=5, early_start_day=0,
            description="Dig foundation"
        )
        p_task2 = PlanTask(
            id="pt2", name="Pour", category=TaskCategory.STRUCTURE,
            duration_days=2, early_start_day=5,
            description="Pour concrete"
        )
        dep = PlanDependency(predecessor_task_id="pt1", successor_task_id="pt2")
        
        plan = PlanOfWork(
            id="plan1", cost_model_id="cost1",
            tasks=[p_task1, p_task2],
            all_dependencies=[dep]
        )
        
        # Import
        ids = service.import_from_plan_of_work(ctx_a, plan, now)
        assert len(ids) == 2
        
        # Verify Tasks
        t1 = service.list_tasks(ctx_a, filters={"lane_id": TaskCategory.FOUNDATION.value})[0]
        t2 = service.list_tasks(ctx_a, filters={"lane_id": TaskCategory.STRUCTURE.value})[0]
        
        assert t1.title == "Dig"
        assert t1.duration_ms == 5 * 24 * 3600 * 1000
        assert t1.start_ts == now
        
        assert t2.title == "Pour"
        assert t2.start_ts == now + timedelta(days=5)
        
        # Verify Dependency
        # Need to find the mapped IDs
        deps = service.get_dependencies(ctx_a)
        assert len(deps) == 1
        assert deps[0].from_task_id == t1.id
        assert deps[0].to_task_id == t2.id
        
        # Idempotency check: import again
        ids_2 = service.import_from_plan_of_work(ctx_a, plan, now)
        assert ids_2 == ids # Same IDs
        assert len(service.list_tasks(ctx_a)) == 2 # No duplicates

    def test_import_boq(self, service, ctx_a):
        """Test importing BoQ items."""
        now = datetime.now(timezone.utc)
        
        scope = Scope(scope_id="sc1", scope_name="Ground Floor")
        item = BoQItem(
            id="bi1", element_type="wall", quantity=100, unit=UnitType.M2,
            formula_used=FormulaType.WALL_AREA, scope_id="sc1"
        )
        boq = BoQModel(
            semantic_model_id="sem1",
            scopes=[scope],
            items=[item]
        )
        
        ids = service.import_from_boq(ctx_a, boq, now)
        assert len(ids) == 1
        
        t = service.get_task(ctx_a, ids[0])
        assert t.title == "wall - 100.0 m²"
        assert t.group_id == "Ground Floor"
        assert t.lane_id == "wall"
    def test_import_content_plan(self, service, ctx_a):
        """Test importing content plan."""
        now = datetime.now(timezone.utc)
        
        item1 = ContentPlanItem(
            id="cp1", campaign="Summer25", channel="Instagram", asset="Hero Video",
            due_date=now, owner="Alice", tags=["video", "social"]
        )
        item2 = ContentPlanItem(
            id="cp2", campaign="Summer25", channel="Email", asset="Launch Blast",
            due_date=now + timedelta(days=2), owner="Bob"
        )
        
        plan = ContentPlanPayload(items=[item1, item2])
        
        ids = service.import_from_content_plan(ctx_a, plan)
        assert len(ids) == 2
        
        t1 = service.get_task(ctx_a, ids[0])
        assert t1.title == "Summer25 - Hero Video (Instagram)"
        assert t1.group_id == "Summer25"
        assert t1.lane_id == "Instagram"
        assert t1.start_ts == now
        assert "owner:Alice" in t1.tags
        assert "video" in t1.tags
        
    def test_gantt_view(self, service, ctx_a):
        """Test Gantt view model generation."""
        now = datetime.now(timezone.utc)
        
        # Create tasks with structure
        # Group 1: Phase A
        t1 = self.create_task("t1", "Task 1", ctx_a)
        t1.group_id = "Phase A"
        t1.lane_id = "Dev"
        t1.duration_ms = 3600*1000
        
        t2 = self.create_task("t2", "Task 2", ctx_a)
        t2.group_id = "Phase A"
        t2.lane_id = "Dev"
        t2.start_ts = now + timedelta(hours=2) # Starts after t1
        
        t3 = self.create_task("t3", "Task 3", ctx_a)
        t3.group_id = "Phase A"
        t3.lane_id = "QA" # Different lane
        
        # Unscoped
        t4 = self.create_task("t4", "Loose Task", ctx_a)
        
        service.create_task(ctx_a, t1)
        service.create_task(ctx_a, t2)
        service.create_task(ctx_a, t3)
        service.create_task(ctx_a, t4)
        
        # Dependency: t1 -> t2
        service.add_dependency(ctx_a, "t1", "t2")
        
        # Get View
        view = service.get_gantt_view(ctx_a)
        
        # Verify Unscoped
        assert len(view.unscoped_items) == 1
        assert view.unscoped_items[0].label == "Loose Task"
        
        # Verify Rows
        assert len(view.rows) == 1
        row = view.rows[0]
        assert row.id == "Phase A"
        assert len(row.sub_rows) == 2 # Dev, QA
        
        # Check sub-rows
        dev_row = next(r for r in row.sub_rows if r.id == "Dev")
        qa_row = next(r for r in row.sub_rows if r.id == "QA")
        
        assert len(dev_row.items) == 2
        assert len(qa_row.items) == 1
        
        # Check Item detail & Dependency
        item_t2 = next(i for i in dev_row.items if i.id == "t2")
        assert item_t2.dependencies == ["t1"]
        # TL02: Check defaults
        assert item_t2.color is None

    def test_gantt_visuals(self, service, ctx_a):
        # Test adapter visuals mapping
        from engines.timeline_core.models import ContentPlanPayload, ContentPlanItem
        
        plan = ContentPlanPayload(items=[
            ContentPlanItem(
                id="c1", campaign="Launch", channel="YouTube",
                asset="Video", due_date=datetime.now(timezone.utc), tags=[]
            )
        ])
        service.import_from_content_plan(ctx_a, plan)
        
        view = service.get_gantt_view(ctx_a)
        # Find the item
        found_item = None
        for row in view.rows:
            for sub in row.sub_rows:
                if sub.items:
                    found_item = sub.items[0]
                    break
        
        assert found_item
        assert found_item.icon == "youtube"
        assert found_item.color is not None
        assert "Campaign" in found_item.tooltip

