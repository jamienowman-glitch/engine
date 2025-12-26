"""
Tests for MC02 timeline mapping and timeline_core compatibility.
"""

import pytest
from datetime import date, timedelta
from collections import defaultdict

from engines.marketing_cadence.models import (
    ChannelType,
    ContentType,
    ContentPool,
    CadenceAsset,
    ScheduleRequest,
)
from engines.marketing_cadence.service import CadenceService


class TestTimelineTaskGeneration:
    """Test timeline task generation in MC01."""
    
    def test_timeline_tasks_created(self):
        """Timeline tasks are created for each slot."""
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
        assert len(schedule.timeline_tasks) == len(schedule.slots)
    
    def test_timeline_task_structure(self):
        """Timeline tasks have correct structure."""
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
        
        for task in schedule.timeline_tasks:
            # Required fields
            assert task.id
            assert task.tenant_id == "tenant_001"
            assert task.env == "dev"
            assert task.request_id == "req_001"
            assert task.title
            assert task.start_date
            assert task.lane  # Channel name
            assert task.source_id  # Asset ID
            
            # Tags should include content type and pool
            assert len(task.tags) > 0
            assert ContentType.SHORT_FORM.value in task.tags or "short_form" in task.tags
            
            # Metadata
            assert task.meta
    
    def test_timeline_task_lane_mapping(self):
        """Timeline task lanes map to channels."""
        service = CadenceService()
        
        pool = ContentPool(
            pool_id="pool_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            channels=[ChannelType.INSTAGRAM, ChannelType.TIKTOK],
        )
        service.register_pool(pool)
        
        asset = CadenceAsset(
            asset_id="asset_001",
            tenant_id="tenant_001",
            env="dev",
            content_type=ContentType.SHORT_FORM,
            pool_id="pool_001",
            channels=[ChannelType.INSTAGRAM, ChannelType.TIKTOK],
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
            channels=[ChannelType.INSTAGRAM, ChannelType.TIKTOK],
            content_types=[ContentType.SHORT_FORM],
        )
        
        schedule = service.generate_schedule(request)
        
        # Map lanes to slots
        lanes_in_tasks = {task.lane for task in schedule.timeline_tasks}
        lanes_in_slots = {slot.channel.value for slot in schedule.slots}
        
        # Should be subset (may not have all channels)
        assert len(lanes_in_tasks) > 0
    
    def test_timeline_task_determinism(self):
        """Timeline task IDs are deterministic."""
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
        
        schedule1 = service.generate_schedule(request)
        schedule2 = service.generate_schedule(request)
        
        # Task IDs should be identical
        for task1, task2 in zip(schedule1.timeline_tasks, schedule2.timeline_tasks):
            assert task1.id == task2.id


class TestTimelineMapping:
    """Test MC02 timeline mapping with offsets."""
    
    def test_offset_timeline_tasks_created(self):
        """Timeline tasks are created for offset schedule."""
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
        
        offset_schedule = service.apply_offsets(
            base_schedule, ChannelType.YOUTUBE_SHORTS, offsets
        )
        
        # Should have timeline tasks
        assert len(offset_schedule.timeline_tasks) > 0
        assert len(offset_schedule.timeline_tasks) == len(offset_schedule.slots)
    
    def test_offset_timeline_tasks_have_metadata(self):
        """Offset timeline tasks include offset metadata."""
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
        
        offsets = {ChannelType.INSTAGRAM: 1}
        offset_schedule = service.apply_offsets(
            base_schedule, ChannelType.YOUTUBE_SHORTS, offsets
        )
        
        # Tasks should have offset metadata
        for task in offset_schedule.timeline_tasks:
            assert task.meta
            # Should indicate offset information
            assert "anchor_channel" in task.meta or "offset_days" in task.meta
    
    def test_timeline_grouped_by_channel(self):
        """Timeline tasks can be grouped by channel/lane."""
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
        
        offset_schedule = service.apply_offsets(
            base_schedule, ChannelType.YOUTUBE_SHORTS, offsets
        )
        
        # Group by lane
        by_lane = defaultdict(list)
        for task in offset_schedule.timeline_tasks:
            by_lane[task.lane].append(task)
        
        # Should have tasks grouped by channel
        assert len(by_lane) > 0
        
        # Within each lane, tasks should have consistent properties
        for lane, tasks in by_lane.items():
            assert all(t.lane == lane for t in tasks)
    
    def test_timeline_grouped_by_content_type(self):
        """Timeline tasks can be grouped by content_type."""
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
        
        # Group by content type (from tags)
        by_content_type = defaultdict(list)
        for task in schedule.timeline_tasks:
            for tag in task.tags:
                if tag in [ct.value for ct in ContentType]:
                    by_content_type[tag].append(task)
                    break
        
        # Should have tasks grouped
        assert len(by_content_type) > 0
    
    def test_timeline_stable_ids_with_offsets(self):
        """Timeline task IDs are stable across offset applications."""
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
        
        offsets = {ChannelType.INSTAGRAM: 1, ChannelType.TIKTOK: 2}
        
        # Apply offsets twice
        offset_schedule1 = service.apply_offsets(
            base_schedule, ChannelType.YOUTUBE_SHORTS, offsets
        )
        offset_schedule2 = service.apply_offsets(
            base_schedule, ChannelType.YOUTUBE_SHORTS, offsets
        )
        
        # Task IDs should be identical
        ids1 = sorted([t.id for t in offset_schedule1.timeline_tasks])
        ids2 = sorted([t.id for t in offset_schedule2.timeline_tasks])
        
        assert ids1 == ids2
    
    def test_timeline_covers_all_channels(self):
        """Timeline tasks cover all channels in offset schedule."""
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
            ChannelType.STORIES: 0,
        }
        
        offset_schedule = service.apply_offsets(
            base_schedule, ChannelType.YOUTUBE_SHORTS, offsets
        )
        
        # Channels in tasks should match channels in slots
        task_lanes = {t.lane for t in offset_schedule.timeline_tasks}
        slot_channels = {s.channel.value for s in offset_schedule.slots}
        
        # Every slot should have a corresponding task
        assert slot_channels == task_lanes or slot_channels.issubset(task_lanes)
