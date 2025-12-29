
import pytest
from datetime import datetime, timedelta, timezone
from pydantic import ValidationError

from engines.timeline_core.models import Task, TaskStatus

def test_task_dates_valid():
    start = datetime.now(timezone.utc)
    t = Task(
        tenant_id="t_1",
        env="dev",
        request_id="r1",
        title="Valid Task",
        start_ts=start,
        end_ts=start + timedelta(hours=1)
    )
    assert t.end_ts > t.start_ts

def test_task_invalid_dates():
    start = datetime.now(timezone.utc)
    with pytest.raises(ValidationError) as exc:
        Task(
            tenant_id="t_1",
            env="dev",
            request_id="r1",
            title="Invalid Task",
            start_ts=start + timedelta(hours=1),
            end_ts=start
        )
    assert "start_ts must be <= end_ts" in str(exc.value)

def test_task_invalid_duration():
    start = datetime.now(timezone.utc)
    with pytest.raises(ValidationError) as exc:
        Task(
            tenant_id="t_1",
            env="dev",
            request_id="r1",
            title="Invalid Duration",
            start_ts=start,
            duration_ms=-100.0
        )
    assert "duration_ms must be non-negative" in str(exc.value)

def test_dependency_self_ref():
    s = TaskStatus.TODO
    # No explicit service needed as models are largely sufficient for unit testing rules,
    # but `add_dependency` logic is in service. We need a dummy service instance.
    from engines.timeline_core.service import TimelineService
    svc = TimelineService()
    ctx = {"tenant_id": "t_1", "env": "dev"}
    
    t1 = Task(tenant_id="t_1", env="dev", request_id="r1", title="T1", start_ts=datetime.now(timezone.utc))
    svc.create_task(ctx, t1)
    
    with pytest.raises(ValueError) as exc:
        svc.add_dependency(ctx, t1.id, t1.id)
    assert "Cannot depend on self" in str(exc.value)

def test_dependency_cycle():
    from engines.timeline_core.service import TimelineService
    svc = TimelineService()
    ctx = {"tenant_id": "t_1", "env": "dev"}
    
    t1 = Task(tenant_id="t_1", env="dev", request_id="r1", title="T1", start_ts=datetime.now(timezone.utc))
    t2 = Task(tenant_id="t_1", env="dev", request_id="r2", title="T2", start_ts=datetime.now(timezone.utc))
    svc.create_task(ctx, t1)
    svc.create_task(ctx, t2)
    
    svc.add_dependency(ctx, t1.id, t2.id)
    
    with pytest.raises(ValueError) as exc:
        svc.add_dependency(ctx, t2.id, t1.id)
    assert "Cycle detected" in str(exc.value)
