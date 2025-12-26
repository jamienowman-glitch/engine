"""
Tests for marketing cadence models.
"""

import pytest
from datetime import datetime, date, timedelta

from engines.marketing_cadence.models import (
    ChannelType,
    ContentType,
    ContentPool,
    CadenceAsset,
    ScheduleRequest,
    ScheduleSlot,
    ConflictReport,
    TimelineTask,
    CooldownRule,
    generate_deterministic_slot_id,
    generate_deterministic_task_id,
)


class TestEnums:
    """Test enum definitions."""
    
    def test_channel_types(self):
        """Verify ChannelType enum values."""
        assert ChannelType.INSTAGRAM.value == "instagram"
        assert ChannelType.TIKTOK.value == "tiktok"
        assert ChannelType.YOUTUBE_SHORTS.value == "youtube_shorts"
        assert ChannelType.EMAIL.value == "email"
    
    def test_content_types(self):
        """Verify ContentType enum values."""
        assert ContentType.STORIES.value == "stories"
        assert ContentType.SHORT_FORM.value == "short_form"
        assert ContentType.LONG_FORM.value == "long_form"
        assert ContentType.EMAIL_BROADCAST.value == "email_broadcast"


class TestContentPool:
    """Test ContentPool model."""
    
    def test_create_pool(self):
        """Create a basic pool."""
        pool = ContentPool(
            pool_id="pool_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.STORIES,
            channels=[ChannelType.INSTAGRAM, ChannelType.STORIES],
            min_days_between_repeats=3,
        )
        assert pool.pool_id == "pool_001"
        assert pool.min_days_between_repeats == 3
        assert len(pool.channels) == 2
    
    def test_pool_defaults(self):
        """Test pool default values."""
        pool = ContentPool(
            pool_id="pool_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.STORIES,
        )
        assert pool.tags == {}
        assert pool.meta == {}
        assert pool.min_days_between_repeats == 0
    
    def test_pool_hash(self):
        """Test pool hashing."""
        pool1 = ContentPool(
            pool_id="pool_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.STORIES,
        )
        pool2 = ContentPool(
            pool_id="pool_001",
            tenant_id="tenant_002",
            env="prod",
            content_type=ContentType.SHORT_FORM,
        )
        # Hash should be based on pool_id
        assert hash(pool1) == hash(pool2)


class TestCadenceAsset:
    """Test CadenceAsset model."""
    
    def test_create_asset(self):
        """Create a basic asset."""
        asset = CadenceAsset(
            asset_id="asset_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            pool_id="pool_001",
            channels=[ChannelType.TIKTOK, ChannelType.INSTAGRAM],
            cooldown_days=14,
        )
        assert asset.asset_id == "asset_001"
        assert asset.pool_id == "pool_001"
        assert asset.cooldown_days == 14
    
    def test_asset_requires_pool(self):
        """Asset must belong to a pool."""
        with pytest.raises(ValueError, match="pool_id required"):
            CadenceAsset(
                asset_id="asset_001",
                tenant_id="tenant_001",
                env="dev",
                content_type=ContentType.SHORT_FORM,
                pool_id="",  # Empty pool_id
                channels=[ChannelType.TIKTOK],
            )
    
    def test_asset_defaults(self):
        """Test asset default values."""
        asset = CadenceAsset(
            asset_id="asset_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            pool_id="pool_001",
        )
        assert asset.cooldown_days == 0
        assert asset.channels == []


class TestScheduleRequest:
    """Test ScheduleRequest model."""
    
    def test_create_request(self):
        """Create a basic schedule request."""
        start = date(2025, 1, 1)
        end = date(2025, 1, 14)
        request = ScheduleRequest(
            request_id="req_001",
            tenant_id="tenant_001",
            env="dev",
            start_date=start,
            end_date=end,
            pool_ids=["pool_001"],
            channels=[ChannelType.INSTAGRAM, ChannelType.TIKTOK],
            content_types=[ContentType.SHORT_FORM],
        )
        assert request.request_id == "req_001"
        assert (request.end_date - request.start_date).days == 13
    
    def test_request_date_validation(self):
        """Request start_date must be <= end_date."""
        with pytest.raises(ValueError, match="start_date must be <= end_date"):
            ScheduleRequest(
                request_id="req_001",
                tenant_id="tenant_001",
                env="dev",
                start_date=date(2025, 1, 14),
                end_date=date(2025, 1, 1),
            )
    
    def test_request_with_caps_override(self):
        """Request can override default caps."""
        request = ScheduleRequest(
            request_id="req_001",
            tenant_id="tenant_001",
            env="dev",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 14),
            global_daily_cap_soft=6,
            global_daily_cap_hard=12,
            channel_caps={
                ChannelType.INSTAGRAM: 4,
                ChannelType.TIKTOK: 3,
            },
        )
        assert request.global_daily_cap_soft == 6
        assert request.global_daily_cap_hard == 12
        assert request.channel_caps[ChannelType.INSTAGRAM] == 4


class TestScheduleSlot:
    """Test ScheduleSlot model."""
    
    def test_create_slot(self):
        """Create a schedule slot."""
        slot = ScheduleSlot(
            slot_id="slot_001",
            asset_id="asset_001",
            pool_id="pool_001",
            content_type=ContentType.SHORT_FORM,
            channel=ChannelType.INSTAGRAM,
            scheduled_date=date(2025, 1, 1),
            priority=0,
        )
        assert slot.slot_id == "slot_001"
        assert slot.asset_id == "asset_001"
        assert slot.scheduled_date == date(2025, 1, 1)


class TestConflictReport:
    """Test ConflictReport model."""
    
    def test_cooldown_violation(self):
        """Create a cooldown violation conflict."""
        conflict = ConflictReport(
            conflict_type="cooldown_violation",
            asset_id="asset_001",
            channel=ChannelType.INSTAGRAM,
            scheduled_date=date(2025, 1, 15),
            message="Asset cooldown violated",
            severity="warning",
        )
        assert conflict.conflict_type == "cooldown_violation"
        assert conflict.severity == "warning"
    
    def test_cap_exceeded(self):
        """Create a cap exceeded conflict."""
        conflict = ConflictReport(
            conflict_type="cap_exceeded",
            channel=ChannelType.TIKTOK,
            scheduled_date=date(2025, 1, 15),
            message="Daily cap reached",
            severity="error",
        )
        assert conflict.conflict_type == "cap_exceeded"
        assert conflict.severity == "error"


class TestTimelineTask:
    """Test TimelineTask model."""
    
    def test_create_task(self):
        """Create a timeline task."""
        task = TimelineTask(
            id="task_001",
            tenant_id="tenant_001",
            env="dev",
            request_id="req_001",
            title="Short-form on Instagram",
            start_date=date(2025, 1, 1),
            lane="instagram",
            tags=["short_form", "pool_001"],
            source_id="asset_001",
        )
        assert task.id == "task_001"
        assert task.lane == "instagram"
        assert len(task.tags) == 2
    
    def test_task_defaults(self):
        """Test task default values."""
        task = TimelineTask(
            id="task_001",
            tenant_id="tenant_001",
            env="dev",
            request_id="req_001",
            title="Test",
            start_date=date(2025, 1, 1),
            lane="instagram",
            source_id="asset_001",
        )
        assert task.tags == []
        assert task.meta == {}


class TestCooldownRule:
    """Test CooldownRule model."""
    
    def test_create_rule(self):
        """Create a cooldown rule."""
        rule = CooldownRule(
            min_days_between_repeats=3,
            asset_cooldown_days=28,
        )
        assert rule.min_days_between_repeats == 3
        assert rule.asset_cooldown_days == 28
    
    def test_rule_hash(self):
        """Cooldown rules are hashable."""
        rule1 = CooldownRule(min_days_between_repeats=3, asset_cooldown_days=28)
        rule2 = CooldownRule(min_days_between_repeats=3, asset_cooldown_days=28)
        # Identical rules should hash the same
        assert hash(rule1) == hash(rule2)


class TestDeterministicIds:
    """Test deterministic ID generation."""
    
    def test_slot_id_deterministic(self):
        """Slot IDs are deterministic for same inputs."""
        id1 = generate_deterministic_slot_id(
            "tenant_001",
            "dev",
            "req_001",
            "asset_001",
            ChannelType.INSTAGRAM,
            date(2025, 1, 1),
        )
        id2 = generate_deterministic_slot_id(
            "tenant_001",
            "dev",
            "req_001",
            "asset_001",
            ChannelType.INSTAGRAM,
            date(2025, 1, 1),
        )
        assert id1 == id2
        assert len(id1) == 16
    
    def test_slot_id_differs_for_different_assets(self):
        """Slot IDs differ for different assets."""
        id1 = generate_deterministic_slot_id(
            "tenant_001",
            "dev",
            "req_001",
            "asset_001",
            ChannelType.INSTAGRAM,
            date(2025, 1, 1),
        )
        id2 = generate_deterministic_slot_id(
            "tenant_001",
            "dev",
            "req_001",
            "asset_002",
            ChannelType.INSTAGRAM,
            date(2025, 1, 1),
        )
        assert id1 != id2
    
    def test_task_id_deterministic(self):
        """Task IDs are deterministic for same inputs."""
        id1 = generate_deterministic_task_id(
            "tenant_001",
            "dev",
            "req_001",
            "asset_001",
            ChannelType.INSTAGRAM,
            date(2025, 1, 1),
            offset_days=0,
        )
        id2 = generate_deterministic_task_id(
            "tenant_001",
            "dev",
            "req_001",
            "asset_001",
            ChannelType.INSTAGRAM,
            date(2025, 1, 1),
            offset_days=0,
        )
        assert id1 == id2
    
    def test_task_id_differs_with_offset(self):
        """Task IDs differ when offset is different."""
        id1 = generate_deterministic_task_id(
            "tenant_001",
            "dev",
            "req_001",
            "asset_001",
            ChannelType.INSTAGRAM,
            date(2025, 1, 1),
            offset_days=0,
        )
        id2 = generate_deterministic_task_id(
            "tenant_001",
            "dev",
            "req_001",
            "asset_001",
            ChannelType.INSTAGRAM,
            date(2025, 1, 1),
            offset_days=1,
        )
        assert id1 != id2
