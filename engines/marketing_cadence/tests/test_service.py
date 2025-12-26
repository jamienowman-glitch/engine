"""
Tests for marketing cadence service.
"""

import pytest
from datetime import date, timedelta

from engines.marketing_cadence.models import (
    ChannelType,
    ContentType,
    ContentPool,
    CadenceAsset,
    ScheduleRequest,
)
from engines.marketing_cadence.service import CadenceService


class TestPoolManagement:
    """Test pool CRUD operations."""
    
    def test_register_and_get_pool(self):
        """Register and retrieve a pool."""
        service = CadenceService()
        pool = ContentPool(
            pool_id="pool_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.STORIES,
            min_days_between_repeats=3,
        )
        
        pool_id = service.register_pool(pool)
        assert pool_id == "pool_001"
        
        retrieved = service.get_pool(pool_id)
        assert retrieved is not None
        assert retrieved.pool_id == "pool_001"
        assert retrieved.min_days_between_repeats == 3
    
    def test_list_pools_by_tenant(self):
        """List pools for a specific tenant."""
        service = CadenceService()
        pool1 = ContentPool(
            pool_id="pool_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.STORIES,
        )
        pool2 = ContentPool(
            pool_id="pool_002",
            tenant_id="tenant_002",
            env="dev",
            content_type=ContentType.SHORT_FORM,
        )
        pool3 = ContentPool(
            pool_id="pool_003",
            tenant_id="tenant_001",
            env="prod",
            content_type=ContentType.STORIES,
        )
        
        service.register_pool(pool1)
        service.register_pool(pool2)
        service.register_pool(pool3)
        
        # List pools for tenant_001, env=dev
        pools = service.list_pools("tenant_001", "dev")
        assert len(pools) == 1
        assert pools[0].pool_id == "pool_001"


class TestAssetManagement:
    """Test asset CRUD operations."""
    
    def test_register_and_get_asset(self):
        """Register and retrieve an asset."""
        service = CadenceService()
        asset = CadenceAsset(
            asset_id="asset_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            pool_id="pool_001",
            cooldown_days=14,
        )
        
        asset_id = service.register_asset(asset)
        assert asset_id == "asset_001"
        
        retrieved = service.get_asset(asset_id)
        assert retrieved is not None
        assert retrieved.cooldown_days == 14
    
    def test_list_assets_by_pool(self):
        """List assets in a pool."""
        service = CadenceService()
        asset1 = CadenceAsset(
            asset_id="asset_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            pool_id="pool_001",
        )
        asset2 = CadenceAsset(
            asset_id="asset_002",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            pool_id="pool_001",
        )
        asset3 = CadenceAsset(
            asset_id="asset_003",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            pool_id="pool_002",
        )
        
        service.register_asset(asset1)
        service.register_asset(asset2)
        service.register_asset(asset3)
        
        pool_assets = service.list_assets_by_pool("pool_001")
        assert len(pool_assets) == 2
        assert all(a.pool_id == "pool_001" for a in pool_assets)


class TestScheduleGeneration:
    """Test schedule generation with cooldowns and caps."""
    
    def test_basic_schedule_generation(self):
        """Generate a basic schedule."""
        service = CadenceService()
        
        # Register pool and assets
        pool = ContentPool(
            pool_id="pool_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            channels=[ChannelType.INSTAGRAM, ChannelType.TIKTOK],
            min_days_between_repeats=1,
        )
        service.register_pool(pool)
        
        asset = CadenceAsset(
            asset_id="asset_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            pool_id="pool_001",
            channels=[ChannelType.INSTAGRAM, ChannelType.TIKTOK],
            cooldown_days=0,
        )
        service.register_asset(asset)
        
        # Generate schedule
        request = ScheduleRequest(
            request_id="req_001",
            tenant_id="tenant_001",
            env="dev",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 3),
            pool_ids=["pool_001"],
            asset_ids=["asset_001"],
            channels=[ChannelType.INSTAGRAM],
            content_types=[ContentType.SHORT_FORM],
        )
        
        schedule = service.generate_schedule(request)
        
        assert schedule.request_id == "req_001"
        assert len(schedule.slots) > 0
        assert all(s.channel == ChannelType.INSTAGRAM for s in schedule.slots)
        assert all(s.content_type == ContentType.SHORT_FORM for s in schedule.slots)
    
    def test_schedule_determinism(self):
        """Same inputs produce same schedule."""
        service = CadenceService()
        
        # Setup
        pool = ContentPool(
            pool_id="pool_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            channels=[ChannelType.INSTAGRAM],
        )
        service.register_pool(pool)
        
        asset = CadenceAsset(
            asset_id="asset_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            pool_id="pool_001",
            channels=[ChannelType.INSTAGRAM],
        )
        service.register_asset(asset)
        
        request = ScheduleRequest(
            request_id="req_001",
            tenant_id="tenant_001",
            env="dev",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 7),
            pool_ids=["pool_001"],
            asset_ids=["asset_001"],
            channels=[ChannelType.INSTAGRAM],
            content_types=[ContentType.SHORT_FORM],
        )
        
        # Generate twice
        schedule1 = service.generate_schedule(request)
        schedule2 = service.generate_schedule(request)
        
        # Slots should be identical (deterministic ordering)
        assert len(schedule1.slots) == len(schedule2.slots)
        for slot1, slot2 in zip(schedule1.slots, schedule2.slots):
            assert slot1.slot_id == slot2.slot_id
            assert slot1.scheduled_date == slot2.scheduled_date
            assert slot1.channel == slot2.channel
    
    def test_asset_cooldown_enforcement(self):
        """Asset cooldowns are respected."""
        service = CadenceService()
        
        # Register pool and asset with 3-day cooldown
        pool = ContentPool(
            pool_id="pool_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            channels=[ChannelType.INSTAGRAM],
        )
        service.register_pool(pool)
        
        asset = CadenceAsset(
            asset_id="asset_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            pool_id="pool_001",
            channels=[ChannelType.INSTAGRAM],
            cooldown_days=3,
        )
        service.register_asset(asset)
        
        # Generate schedule
        request = ScheduleRequest(
            request_id="req_001",
            tenant_id="tenant_001",
            env="dev",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 14),
            pool_ids=["pool_001"],
            asset_ids=["asset_001"],
            channels=[ChannelType.INSTAGRAM],
            content_types=[ContentType.SHORT_FORM],
        )
        
        schedule = service.generate_schedule(request)
        
        # Check that slots are at least 3 days apart
        if len(schedule.slots) > 1:
            for i in range(len(schedule.slots) - 1):
                slot1 = schedule.slots[i]
                slot2 = schedule.slots[i + 1]
                if slot1.asset_id == slot2.asset_id:
                    days_apart = (slot2.scheduled_date - slot1.scheduled_date).days
                    assert days_apart >= 3
    
    def test_pool_cooldown_enforcement(self):
        """Pool-level cooldowns are respected."""
        service = CadenceService()
        
        # Pool with 2-day min_days_between_repeats
        pool = ContentPool(
            pool_id="pool_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            channels=[ChannelType.INSTAGRAM],
            min_days_between_repeats=2,
        )
        service.register_pool(pool)
        
        # Multiple assets in same pool
        for i in range(3):
            asset = CadenceAsset(
                asset_id=f"asset_{i:03d}",
                tenant_id="tenant_001",
                env="dev",
                content_type=ContentType.SHORT_FORM,
                pool_id="pool_001",
                channels=[ChannelType.INSTAGRAM],
                cooldown_days=0,
            )
            service.register_asset(asset)
        
        request = ScheduleRequest(
            request_id="req_001",
            tenant_id="tenant_001",
            env="dev",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 14),
            pool_ids=["pool_001"],
            channels=[ChannelType.INSTAGRAM],
            content_types=[ContentType.SHORT_FORM],
        )
        
        schedule = service.generate_schedule(request)
        
        # Group slots by pool
        if len(schedule.slots) > 1:
            pool_slots = schedule.slots
            # Check pool cooldown
            for i in range(len(pool_slots) - 1):
                slot1 = pool_slots[i]
                slot2 = pool_slots[i + 1]
                if slot1.pool_id == slot2.pool_id:
                    days_apart = (slot2.scheduled_date - slot1.scheduled_date).days
                    assert days_apart >= 2
    
    def test_global_cap_enforcement(self):
        """Global daily caps are enforced."""
        service = CadenceService()
        
        # Pool with multiple assets
        pool = ContentPool(
            pool_id="pool_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.STORIES,
            channels=[ChannelType.INSTAGRAM, ChannelType.TIKTOK, ChannelType.STORIES],
        )
        service.register_pool(pool)
        
        # Create 10 assets
        for i in range(10):
            asset = CadenceAsset(
                asset_id=f"asset_{i:03d}",
                tenant_id="tenant_001",
                env="dev",
                content_type=ContentType.STORIES,
                pool_id="pool_001",
                channels=[ChannelType.INSTAGRAM, ChannelType.TIKTOK, ChannelType.STORIES],
                cooldown_days=0,
            )
            service.register_asset(asset)
        
        request = ScheduleRequest(
            request_id="req_001",
            tenant_id="tenant_001",
            env="dev",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 1),  # Single day
            pool_ids=["pool_001"],
            channels=[ChannelType.INSTAGRAM, ChannelType.TIKTOK, ChannelType.STORIES],
            content_types=[ContentType.STORIES],
            global_daily_cap_hard=10,
        )
        
        schedule = service.generate_schedule(request)
        
        # Check that no day exceeds hard cap
        from collections import defaultdict
        daily_count = defaultdict(int)
        for slot in schedule.slots:
            daily_count[slot.scheduled_date] += 1
        
        for count in daily_count.values():
            assert count <= 10
    
    def test_channel_cap_enforcement(self):
        """Per-channel caps are enforced."""
        service = CadenceService()
        
        pool = ContentPool(
            pool_id="pool_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            channels=[ChannelType.INSTAGRAM],
        )
        service.register_pool(pool)
        
        # Create multiple assets
        for i in range(5):
            asset = CadenceAsset(
                asset_id=f"asset_{i:03d}",
                tenant_id="tenant_001",
                env="dev",
                content_type=ContentType.SHORT_FORM,
                pool_id="pool_001",
                channels=[ChannelType.INSTAGRAM],
                cooldown_days=0,
            )
            service.register_asset(asset)
        
        request = ScheduleRequest(
            request_id="req_001",
            tenant_id="tenant_001",
            env="dev",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 1),
            pool_ids=["pool_001"],
            channels=[ChannelType.INSTAGRAM],
            content_types=[ContentType.SHORT_FORM],
            channel_caps={ChannelType.INSTAGRAM: 2},
        )
        
        schedule = service.generate_schedule(request)
        
        # Check channel cap
        instagram_count = sum(1 for s in schedule.slots if s.channel == ChannelType.INSTAGRAM)
        assert instagram_count <= 2
    
    def test_conflict_reporting(self):
        """Conflicts are reported in response."""
        service = CadenceService()
        
        pool = ContentPool(
            pool_id="pool_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            channels=[ChannelType.INSTAGRAM],
            min_days_between_repeats=30,  # Long cooldown
        )
        service.register_pool(pool)
        
        asset = CadenceAsset(
            asset_id="asset_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            pool_id="pool_001",
            channels=[ChannelType.INSTAGRAM],
            cooldown_days=0,
        )
        service.register_asset(asset)
        
        request = ScheduleRequest(
            request_id="req_001",
            tenant_id="tenant_001",
            env="dev",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 10),
            pool_ids=["pool_001"],
            asset_ids=["asset_001"],
            channels=[ChannelType.INSTAGRAM],
            content_types=[ContentType.SHORT_FORM],
        )
        
        schedule = service.generate_schedule(request)
        
        # Should have conflicts due to long pool cooldown
        assert len(schedule.conflicts) > 0
        assert any(c.conflict_type == "cooldown_violation" for c in schedule.conflicts)
    
    def test_timeline_tasks_generated(self):
        """Timeline tasks are generated in response."""
        service = CadenceService()
        
        pool = ContentPool(
            pool_id="pool_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            channels=[ChannelType.INSTAGRAM],
        )
        service.register_pool(pool)
        
        asset = CadenceAsset(
            asset_id="asset_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            pool_id="pool_001",
            channels=[ChannelType.INSTAGRAM],
        )
        service.register_asset(asset)
        
        request = ScheduleRequest(
            request_id="req_001",
            tenant_id="tenant_001",
            env="dev",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 7),
            pool_ids=["pool_001"],
            asset_ids=["asset_001"],
            channels=[ChannelType.INSTAGRAM],
            content_types=[ContentType.SHORT_FORM],
        )
        
        schedule = service.generate_schedule(request)
        
        # Should have timeline tasks
        assert len(schedule.timeline_tasks) > 0
        for task in schedule.timeline_tasks:
            assert task.id
            assert task.tenant_id == "tenant_001"
            assert task.env == "dev"
            assert task.lane in ["instagram"]


class TestOffsetApplication:
    """Test MC02 offset application."""
    
    def test_apply_offsets_basic(self):
        """Apply offsets to base schedule."""
        service = CadenceService()
        
        pool = ContentPool(
            pool_id="pool_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            channels=[ChannelType.YOUTUBE_SHORTS],
        )
        service.register_pool(pool)
        
        asset = CadenceAsset(
            asset_id="asset_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            pool_id="pool_001",
            channels=[ChannelType.YOUTUBE_SHORTS],
        )
        service.register_asset(asset)
        
        # Generate base schedule
        request = ScheduleRequest(
            request_id="req_001",
            tenant_id="tenant_001",
            env="dev",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 7),
            pool_ids=["pool_001"],
            asset_ids=["asset_001"],
            channels=[ChannelType.YOUTUBE_SHORTS],
            content_types=[ContentType.SHORT_FORM],
        )
        
        base_schedule = service.generate_schedule(request)
        
        # Apply offsets
        offsets = {
            ChannelType.INSTAGRAM: 1,
            ChannelType.TIKTOK: 2,
        }
        
        offset_schedule = service.apply_offsets(
            base_schedule,
            ChannelType.YOUTUBE_SHORTS,
            offsets,
        )
        
        assert offset_schedule.meta["is_offset_applied"] is True
        assert offset_schedule.meta["anchor_channel"] == "youtube_shorts"
        assert len(offset_schedule.slots) > 0
    
    def test_offset_schedule_determinism(self):
        """Offset schedules are deterministic."""
        service = CadenceService()
        
        pool = ContentPool(
            pool_id="pool_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            channels=[ChannelType.YOUTUBE_SHORTS],
        )
        service.register_pool(pool)
        
        asset = CadenceAsset(
            asset_id="asset_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            pool_id="pool_001",
            channels=[ChannelType.YOUTUBE_SHORTS],
        )
        service.register_asset(asset)
        
        request = ScheduleRequest(
            request_id="req_001",
            tenant_id="tenant_001",
            env="dev",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 7),
            pool_ids=["pool_001"],
            asset_ids=["asset_001"],
            channels=[ChannelType.YOUTUBE_SHORTS],
            content_types=[ContentType.SHORT_FORM],
        )
        
        base_schedule = service.generate_schedule(request)
        
        offsets = {
            ChannelType.INSTAGRAM: 1,
            ChannelType.TIKTOK: 2,
        }
        
        offset_schedule1 = service.apply_offsets(
            base_schedule, ChannelType.YOUTUBE_SHORTS, offsets
        )
        offset_schedule2 = service.apply_offsets(
            base_schedule, ChannelType.YOUTUBE_SHORTS, offsets
        )
        
        # Should be identical
        assert len(offset_schedule1.slots) == len(offset_schedule2.slots)
        for slot1, slot2 in zip(offset_schedule1.slots, offset_schedule2.slots):
            assert slot1.slot_id == slot2.slot_id
    
    def test_offset_dates_applied_correctly(self):
        """Offsets are applied to correct dates."""
        service = CadenceService()
        
        pool = ContentPool(
            pool_id="pool_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            channels=[ChannelType.YOUTUBE_SHORTS],
        )
        service.register_pool(pool)
        
        asset = CadenceAsset(
            asset_id="asset_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            pool_id="pool_001",
            channels=[ChannelType.YOUTUBE_SHORTS],
        )
        service.register_asset(asset)
        
        request = ScheduleRequest(
            request_id="req_001",
            tenant_id="tenant_001",
            env="dev",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 3),
            pool_ids=["pool_001"],
            asset_ids=["asset_001"],
            channels=[ChannelType.YOUTUBE_SHORTS],
            content_types=[ContentType.SHORT_FORM],
        )
        
        base_schedule = service.generate_schedule(request)
        
        # Apply offset: IG gets +1 day
        offsets = {ChannelType.INSTAGRAM: 1}
        offset_schedule = service.apply_offsets(
            base_schedule, ChannelType.YOUTUBE_SHORTS, offsets
        )
        
        # Find Instagram slots and verify offset
        ig_slots = [s for s in offset_schedule.slots if s.channel == ChannelType.INSTAGRAM]
        if ig_slots and base_schedule.slots:
            base_date = base_schedule.slots[0].scheduled_date
            for ig_slot in ig_slots:
                if ig_slot.asset_id == base_schedule.slots[0].asset_id:
                    # Should be at least 1 day offset
                    date_diff = (ig_slot.scheduled_date - base_date).days
                    assert date_diff >= 1
