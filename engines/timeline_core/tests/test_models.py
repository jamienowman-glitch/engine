"""
Tests for Timeline Core Models.
"""

import pytest
from datetime import datetime, timedelta, timezone
from engines.timeline_core.models import Task, TaskStatus, Dependency, DependencyType

class TestTimelineModels:
    
    def test_task_creation_valid(self):
        """Test creating a valid task."""
        now = datetime.now(timezone.utc)
        t = Task(
            tenant_id="t1",
            env="dev",
            request_id="req1",
            title="My Task",
            start_ts=now,
            end_ts=now + timedelta(hours=1),
            status=TaskStatus.TODO
        )
        assert t.id is not None
        assert t.status == TaskStatus.TODO
        assert t.duration_ms is None # Optional

    def test_task_date_validation(self):
        """Test start_ts <= end_ts validation."""
        now = datetime.now(timezone.utc)
        # Invalid: start > end
        with pytest.raises(ValueError, match="start_ts must be <= end_ts"):
            Task(
                tenant_id="t1",
                env="dev",
                request_id="req1",
                title="Bad Task",
                start_ts=now + timedelta(hours=1),
                end_ts=now
            )

    def test_deterministic_id_generation(self):
        """Test deterministic ID generation."""
        tid = "t1"
        env = "dev"
        kind = "cad"
        sid = "abc"
        
        id1 = Task.generate_deterministic_id(tid, env, kind, sid)
        id2 = Task.generate_deterministic_id(tid, env, kind, sid)
        
        assert id1 == id2
        assert len(id1) == 64 # SHA256 hex
        
        # Change one input
        id3 = Task.generate_deterministic_id(tid, "prod", kind, sid)
        assert id1 != id3

    def test_dependency_defaults(self):
        """Test dependency defaults."""
        d = Dependency(from_task_id="a", to_task_id="b")
        assert d.type == DependencyType.FINISH_TO_START

    def test_deterministic_id_cad_scenario(self):
        """
        Verify determinism for CAD-derived tasks.
        Scenario: BoQ item with known ID defines the task.
        """
        tenant_id = "tenant_cad"
        env = "prod"
        source_kind = "boq_item"
        boq_item_id = "wall_001_hash"
        
        # Generation 1
        id1 = Task.generate_deterministic_id(tenant_id, env, source_kind, boq_item_id)
        
        # Generation 2 (same inputs)
        id2 = Task.generate_deterministic_id(tenant_id, env, source_kind, boq_item_id)
        
        assert id1 == id2
        
        # Different environment -> Different ID
        id3 = Task.generate_deterministic_id(tenant_id, "dev", source_kind, boq_item_id)
        assert id1 != id3

    def test_deterministic_id_content_scenario(self):
        """
        Verify determinism for Content-derived tasks.
        Scenario: Campaign + Asset define the task.
        """
        tenant_id = "tenant_marketing"
        env = "prod"
        source_kind = "content_asset"
        # Composite source ID constructed by logic (e.g. campaign_id:asset_id)
        # The adapter would be responsible for creating this unique string.
        composite_source_id = "campaign_summer_2025:social_post_01"
        
        id1 = Task.generate_deterministic_id(tenant_id, env, source_kind, composite_source_id)
        id2 = Task.generate_deterministic_id(tenant_id, env, source_kind, composite_source_id)
        
        assert id1 == id2

