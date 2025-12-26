"""
Marketing Cadence Service.

Manages content pools, assets, and schedule generation with cooldowns and caps.
"""

from __future__ import annotations

from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict

from engines.marketing_cadence.models import (
    ChannelType,
    ContentType,
    ContentPool,
    CadenceAsset,
    ScheduleRequest,
    ScheduleSuggestion,
    ScheduleSlot,
    ConflictReport,
    TimelineTask,
    ContentTypeDefaults,
    generate_deterministic_slot_id,
    generate_deterministic_task_id,
)


# ============================================================================
# Default Content Type Configurations
# ============================================================================

DEFAULT_CONTENT_TYPE_CONFIG: Dict[ContentType, ContentTypeDefaults] = {
    ContentType.STORIES: ContentTypeDefaults(
        content_type=ContentType.STORIES,
        pool_min_days_between_repeats=3,
        asset_cooldown_days=28,
        target_per_day_per_channel=3,
        hard_cap_per_day_per_channel=5,
    ),
    ContentType.SHORT_FORM: ContentTypeDefaults(
        content_type=ContentType.SHORT_FORM,
        pool_min_days_between_repeats=14,
        asset_cooldown_days=90,
        target_per_day_per_channel=1,
        hard_cap_per_day_per_channel=3,
    ),
    ContentType.TRIAL_REEL: ContentTypeDefaults(
        content_type=ContentType.TRIAL_REEL,
        pool_min_days_between_repeats=14,
        asset_cooldown_days=90,
        target_per_day_per_channel=1,
        hard_cap_per_day_per_channel=3,
    ),
    ContentType.LONG_FORM: ContentTypeDefaults(
        content_type=ContentType.LONG_FORM,
        pool_min_days_between_repeats=0,  # No auto repeats
        asset_cooldown_days=0,
        target_per_day_per_channel=0,
        hard_cap_per_day_per_channel=1,
    ),
    ContentType.EMAIL_FLOW: ContentTypeDefaults(
        content_type=ContentType.EMAIL_FLOW,
        pool_min_days_between_repeats=1,
        asset_cooldown_days=0,
        target_per_day_per_channel=1,
        hard_cap_per_day_per_channel=1,
    ),
    ContentType.EMAIL_BROADCAST: ContentTypeDefaults(
        content_type=ContentType.EMAIL_BROADCAST,
        pool_min_days_between_repeats=0,
        asset_cooldown_days=0,
        target_per_day_per_channel=0,
        hard_cap_per_day_per_channel=3,
        max_per_week_segment=3,
    ),
    ContentType.DM_FLOW: ContentTypeDefaults(
        content_type=ContentType.DM_FLOW,
        pool_min_days_between_repeats=1,
        asset_cooldown_days=0,
        target_per_day_per_channel=1,
        hard_cap_per_day_per_channel=1,
    ),
    ContentType.DM_BROADCAST: ContentTypeDefaults(
        content_type=ContentType.DM_BROADCAST,
        pool_min_days_between_repeats=0,
        asset_cooldown_days=0,
        target_per_day_per_channel=0,
        hard_cap_per_day_per_channel=2,
        max_per_week_segment=2,
    ),
    ContentType.FEED_CAROUSEL: ContentTypeDefaults(
        content_type=ContentType.FEED_CAROUSEL,
        pool_min_days_between_repeats=7,
        asset_cooldown_days=60,
        target_per_day_per_channel=1,
        hard_cap_per_day_per_channel=2,
    ),
    ContentType.COMMUNITY_POST: ContentTypeDefaults(
        content_type=ContentType.COMMUNITY_POST,
        pool_min_days_between_repeats=7,
        asset_cooldown_days=60,
        target_per_day_per_channel=1,
        hard_cap_per_day_per_channel=2,
    ),
    ContentType.BLOG: ContentTypeDefaults(
        content_type=ContentType.BLOG,
        pool_min_days_between_repeats=0,
        asset_cooldown_days=0,
        target_per_day_per_channel=0,
        hard_cap_per_day_per_channel=1,
    ),
    ContentType.HOMEPAGE_HERO: ContentTypeDefaults(
        content_type=ContentType.HOMEPAGE_HERO,
        pool_min_days_between_repeats=0,
        asset_cooldown_days=14,
        target_per_day_per_channel=0,
        hard_cap_per_day_per_channel=1,
    ),
}


class CadenceService:
    """Service for managing cadence pools, assets, and schedule generation."""
    
    def __init__(self):
        """Initialize in-memory storage."""
        # pools[pool_id] = ContentPool
        self._pools: Dict[str, ContentPool] = {}
        # assets[asset_id] = CadenceAsset
        self._assets: Dict[str, CadenceAsset] = {}
        # Track last scheduled date for each asset (for cooldown)
        # Format: {asset_id: last_scheduled_date}
        self._asset_last_scheduled: Dict[str, date] = {}
        # Track last scheduled date for each pool (for pool cooldown)
        # Format: {pool_id: last_scheduled_date}
        self._pool_last_scheduled: Dict[str, date] = {}
    
    # ========================================================================
    # Pool Management
    # ========================================================================
    
    def register_pool(self, pool: ContentPool) -> str:
        """Register a content pool."""
        self._pools[pool.pool_id] = pool
        return pool.pool_id
    
    def get_pool(self, pool_id: str) -> Optional[ContentPool]:
        """Get a pool by ID."""
        return self._pools.get(pool_id)
    
    def list_pools(self, tenant_id: str, env: str) -> List[ContentPool]:
        """List all pools for a tenant/env."""
        return [
            pool for pool in self._pools.values()
            if pool.tenant_id == tenant_id and pool.env == env
        ]
    
    # ========================================================================
    # Asset Management
    # ========================================================================
    
    def register_asset(self, asset: CadenceAsset) -> str:
        """Register a content asset."""
        self._assets[asset.asset_id] = asset
        return asset.asset_id
    
    def get_asset(self, asset_id: str) -> Optional[CadenceAsset]:
        """Get an asset by ID."""
        return self._assets.get(asset_id)
    
    def list_assets(self, tenant_id: str, env: str) -> List[CadenceAsset]:
        """List all assets for a tenant/env."""
        return [
            asset for asset in self._assets.values()
            if asset.tenant_id == tenant_id and asset.env == env
        ]
    
    def list_assets_by_pool(self, pool_id: str) -> List[CadenceAsset]:
        """List all assets in a specific pool."""
        return [
            asset for asset in self._assets.values()
            if asset.pool_id == pool_id
        ]
    
    # ========================================================================
    # Schedule Generation (MC01)
    # ========================================================================
    
    def generate_schedule(self, request: ScheduleRequest) -> ScheduleSuggestion:
        """
        Generate a deterministic schedule respecting all cooldowns and caps.
        
        This is the core MC01 function that:
        - Respects pool-level min_days_between_repeats
        - Respects asset-level cooldown_days
        - Applies default caps per content_type
        - Enforces global daily caps (soft 5-7/day, hard 10/day)
        - Enforces per-channel caps
        - Returns conflicts for violations
        - Generates timeline_core-compatible tasks
        
        IMPORTANT: This is deterministic and does NOT modify internal state.
        State is only updated when schedules are committed/persisted.
        """
        slots: List[ScheduleSlot] = []
        conflicts: List[ConflictReport] = []
        timeline_tasks: List[TimelineTask] = []
        
        # Determine which pools and assets to schedule
        pools = self._select_pools(request)
        assets = self._select_assets(request, pools)
        
        # Determine date range
        current_date = request.start_date
        
        # Track usage per day/channel to enforce caps (local to this call)
        daily_usage: Dict[date, Dict[ChannelType, int]] = defaultdict(lambda: defaultdict(int))
        global_daily_usage: Dict[date, int] = defaultdict(int)
        
        # Track asset/pool scheduling within THIS request (for cooldowns)
        # Map of {asset_id: [(date_used, channels_used), ...]} to prevent multi-use same day
        asset_schedule_in_request: Dict[str, List[Tuple[date, ChannelType]]] = defaultdict(list)
        # Map of {pool_id: [date_used, ...]} to track pool usage within this request
        pool_schedule_in_request: Dict[str, List[date]] = defaultdict(list)
        
        # Get defaults for each content type
        defaults_by_type: Dict[ContentType, ContentTypeDefaults] = {}
        for ct in request.content_types:
            defaults_by_type[ct] = DEFAULT_CONTENT_TYPE_CONFIG.get(
                ct, ContentTypeDefaults(content_type=ct)
            )
        
        # Get global caps (use provided or defaults)
        global_cap_soft = request.global_daily_cap_soft or 7
        global_cap_hard = request.global_daily_cap_hard or 10
        
        # Round-robin through pools and assets for deterministic, balanced distribution
        available_assets = sorted(
            [a for a in assets if a.asset_id in [aid for aid in request.asset_ids or []]
             or any(a.pool_id == pid for pid in request.pool_ids or [])],
            key=lambda a: (a.pool_id, a.asset_id),  # Deterministic sort
        )
        
        asset_index = 0
        
        while current_date <= request.end_date and available_assets:
            # For each content type, try to add a slot
            for content_type in request.content_types:
                if not available_assets:
                    break
                
                defaults = defaults_by_type.get(content_type)
                if not defaults:
                    continue
                
                # Select channels for this content type
                channels_to_use = [
                    ch for ch in request.channels
                    if ch in [a.channels for a in available_assets for _ in a.channels
                              if content_type == a.content_type]
                ] or request.channels
                
                if not channels_to_use:
                    continue
                
                # For each channel, try to add asset
                for channel in sorted(channels_to_use, key=lambda x: x.value):  # Deterministic order
                    # Check channel cap
                    channel_cap = request.channel_caps.get(
                        channel, defaults.hard_cap_per_day_per_channel
                    )
                    channel_usage = daily_usage[current_date][channel]
                    
                    if channel_usage >= channel_cap:
                        conflicts.append(ConflictReport(
                            conflict_type="cap_exceeded",
                            channel=channel,
                            scheduled_date=current_date,
                            message=f"Channel {channel.value} daily cap ({channel_cap}) reached on {current_date}",
                            severity="warning",
                        ))
                        continue
                    
                    # Check global cap
                    global_usage = global_daily_usage[current_date]
                    if global_usage >= global_cap_hard:
                        conflicts.append(ConflictReport(
                            conflict_type="cap_exceeded",
                            scheduled_date=current_date,
                            message=f"Global hard cap ({global_cap_hard}/day) reached on {current_date}",
                            severity="error",
                        ))
                        break  # Stop adding for this day
                    
                    # Find next available asset (with cooldown check)
                    asset_found = False
                    attempts = 0
                    
                    while attempts < len(available_assets):
                        candidate_asset = available_assets[asset_index % len(available_assets)]
                        asset_index += 1
                        attempts += 1
                        
                        # Check if asset is suitable for this channel/content_type
                        if candidate_asset.content_type != content_type:
                            continue
                        if channel not in candidate_asset.channels:
                            continue
                        
                        # Check if asset was already used in THIS request (no multi-channel same day)
                        asset_uses_in_request = asset_schedule_in_request.get(candidate_asset.asset_id, [])
                        if any(date_used == current_date for date_used, _ in asset_uses_in_request):
                            # Asset already used this day in this request
                            continue
                        
                        # Check asset cooldown (from both global state AND intra-request state)
                        last_scheduled = self._asset_last_scheduled.get(candidate_asset.asset_id)
                        if last_scheduled:
                            days_since = (current_date - last_scheduled).days
                            if days_since < candidate_asset.cooldown_days:
                                conflicts.append(ConflictReport(
                                    conflict_type="cooldown_violation",
                                    asset_id=candidate_asset.asset_id,
                                    channel=channel,
                                    scheduled_date=current_date,
                                    message=f"Asset {candidate_asset.asset_id} cooldown {candidate_asset.cooldown_days}d "
                                           f"violated by global state (last {days_since}d ago)",
                                    severity="warning",
                                ))
                                continue
                        
                        # Also check intra-request asset cooldown
                        if asset_uses_in_request:
                            most_recent_asset_date = max(date_used for date_used, _ in asset_uses_in_request)
                            days_since = (current_date - most_recent_asset_date).days
                            if days_since < candidate_asset.cooldown_days:
                                conflicts.append(ConflictReport(
                                    conflict_type="cooldown_violation",
                                    asset_id=candidate_asset.asset_id,
                                    channel=channel,
                                    scheduled_date=current_date,
                                    message=f"Asset {candidate_asset.asset_id} cooldown {candidate_asset.cooldown_days}d "
                                           f"violated within request (last {days_since}d ago at {most_recent_asset_date})",
                                    severity="warning",
                                ))
                                continue
                        
                        # Check pool cooldown (from both global state AND intra-request state)
                        pool = self.get_pool(candidate_asset.pool_id)
                        if pool:
                            # First check global state
                            last_pool_scheduled = self._pool_last_scheduled.get(pool.pool_id)
                            if last_pool_scheduled:
                                days_since = (current_date - last_pool_scheduled).days
                                if days_since < pool.min_days_between_repeats:
                                    conflicts.append(ConflictReport(
                                        conflict_type="cooldown_violation",
                                        pool_id=pool.pool_id,
                                        channel=channel,
                                        scheduled_date=current_date,
                                        message=f"Pool {pool.pool_id} cooldown {pool.min_days_between_repeats}d "
                                               f"violated by global state (last {days_since}d ago)",
                                        severity="warning",
                                    ))
                                    continue
                            
                            # Also check intra-request pool scheduling
                            pool_dates_in_request = pool_schedule_in_request.get(pool.pool_id, [])
                            if pool_dates_in_request:
                                # Find the most recent pool usage in this request
                                most_recent_pool_date = max(pool_dates_in_request)
                                days_since = (current_date - most_recent_pool_date).days
                                if days_since < pool.min_days_between_repeats:
                                    conflicts.append(ConflictReport(
                                        conflict_type="cooldown_violation",
                                        pool_id=pool.pool_id,
                                        channel=channel,
                                        scheduled_date=current_date,
                                        message=f"Pool {pool.pool_id} cooldown {pool.min_days_between_repeats}d "
                                               f"violated within request (last {days_since}d ago at {most_recent_pool_date})",
                                        severity="warning",
                                    ))
                                    continue
                        
                        # Asset is good; schedule it
                        slot_id = generate_deterministic_slot_id(
                            request.tenant_id, request.env, request.request_id,
                            candidate_asset.asset_id, channel, current_date
                        )
                        
                        slot = ScheduleSlot(
                            slot_id=slot_id,
                            asset_id=candidate_asset.asset_id,
                            pool_id=candidate_asset.pool_id,
                            content_type=content_type,
                            channel=channel,
                            scheduled_date=current_date,
                            priority=0,
                        )
                        slots.append(slot)
                        
                        # Update tracking for THIS CALL ONLY (not global state)
                        daily_usage[current_date][channel] += 1
                        global_daily_usage[current_date] += 1
                        asset_schedule_in_request[candidate_asset.asset_id].append((current_date, channel))
                        pool_schedule_in_request[candidate_asset.pool_id].append(current_date)
                        asset_schedule_in_request[candidate_asset.asset_id].append((current_date, channel))
                        
                        # Generate timeline task
                        task = self._create_timeline_task(
                            request, slot, candidate_asset, pool, offset_days=0
                        )
                        timeline_tasks.append(task)
                        
                        asset_found = True
                        break
                    
                    if not asset_found:
                        conflicts.append(ConflictReport(
                            conflict_type="insufficient_assets",
                            content_type=content_type,
                            channel=channel,
                            scheduled_date=current_date,
                            message=f"No available assets for {content_type.value} on {channel.value} "
                                   f"on {current_date}",
                            severity="warning",
                        ))
            
            current_date += timedelta(days=1)
        
        # Sort slots deterministically
        slots.sort(key=lambda s: (s.scheduled_date, s.channel.value, s.asset_id))
        
        return ScheduleSuggestion(
            request_id=request.request_id,
            tenant_id=request.tenant_id,
            env=request.env,
            slots=slots,
            conflicts=conflicts,
            timeline_tasks=timeline_tasks,
            total_slots=len(slots),
            date_range_start=request.start_date,
            date_range_end=request.end_date,
            meta={
                "global_daily_cap_soft": global_cap_soft,
                "global_daily_cap_hard": global_cap_hard,
            },
        )
    
    # ========================================================================
    # MC02: Offset Application
    # ========================================================================
    
    def apply_offsets(
        self,
        base_schedule: ScheduleSuggestion,
        anchor_channel: ChannelType,
        channel_offsets: Dict[ChannelType, int],
    ) -> ScheduleSuggestion:
        """
        Apply anchor + offsets to create a multi-channel schedule (MC02).
        
        Args:
            base_schedule: Base schedule from MC01 (typically single-channel)
            anchor_channel: Primary channel (Day 0)
            channel_offsets: Offsets in days for other channels
        
        Returns:
            Multi-channel schedule with offsets applied
        """
        offset_slots: List[ScheduleSlot] = []
        offset_tasks: List[TimelineTask] = []
        conflicts = list(base_schedule.conflicts)  # Inherit parent conflicts
        
        # Determine default offsets if not provided
        defaults = {
            ChannelType.INSTAGRAM: 1,
            ChannelType.TIKTOK: 2,
            ChannelType.STORIES: 0,
            ChannelType.EMAIL: 0,
            ChannelType.SMS: 0,
            ChannelType.DM: 0,
            ChannelType.YOUTUBE_SHORTS: 0,
            ChannelType.YOUTUBE_LONGFORM: 0,
            ChannelType.FEED_CAROUSEL: 0,
            ChannelType.COMMUNITY: 0,
            ChannelType.BLOG: 0,
            ChannelType.HOMEPAGE: 0,
        }
        
        # Merge provided offsets with defaults
        offsets_to_apply = {**defaults, **channel_offsets}
        
        # For each slot in base schedule, apply offsets for each channel
        for slot in base_schedule.slots:
            for target_channel, offset_days in offsets_to_apply.items():
                # Create offset slot
                new_date = slot.scheduled_date + timedelta(days=offset_days)
                
                # Check if offset slot still within extended bounds
                # (allow some grace period)
                max_end = base_schedule.date_range_end + timedelta(days=30)
                if new_date > max_end:
                    continue
                
                # Create new slot with offset
                offset_slot_id = generate_deterministic_slot_id(
                    slot.slot_id[:16],  # Use hash prefix
                    base_schedule.env,
                    base_schedule.request_id,
                    slot.asset_id,
                    target_channel,
                    new_date,
                )
                
                offset_slot = ScheduleSlot(
                    slot_id=offset_slot_id,
                    asset_id=slot.asset_id,
                    pool_id=slot.pool_id,
                    content_type=slot.content_type,
                    channel=target_channel,
                    scheduled_date=new_date,
                    priority=slot.priority,
                    meta={
                        **slot.meta,
                        "anchor_channel": anchor_channel.value,
                        "offset_days": offset_days,
                    },
                )
                offset_slots.append(offset_slot)
                
                # Create offset timeline task
                # (Assumes we have access to asset/pool; simplified here)
                asset = self.get_asset(slot.asset_id)
                pool = self.get_pool(slot.pool_id)
                
                task_id = generate_deterministic_task_id(
                    base_schedule.tenant_id,
                    base_schedule.env,
                    base_schedule.request_id,
                    slot.asset_id,
                    target_channel,
                    slot.scheduled_date,
                    offset_days=offset_days,
                )
                
                task = TimelineTask(
                    id=task_id,
                    tenant_id=base_schedule.tenant_id,
                    env=base_schedule.env,
                    request_id=base_schedule.request_id,
                    title=f"{slot.content_type.value} on {target_channel.value} (+{offset_days}d)",
                    start_date=new_date,
                    lane=target_channel.value,
                    tags=[slot.content_type.value, slot.pool_id],
                    source_id=slot.asset_id,
                    meta={
                        "anchor_channel": anchor_channel.value,
                        "offset_days": offset_days,
                        "base_slot_id": slot.slot_id,
                    },
                )
                offset_tasks.append(task)
        
        # Sort slots deterministically
        offset_slots.sort(key=lambda s: (s.scheduled_date, s.channel.value, s.asset_id))
        
        # Check for conflicts after offsets (cooldowns, collisions, etc)
        # For now, inherit conflicts from base
        
        return ScheduleSuggestion(
            request_id=base_schedule.request_id,
            tenant_id=base_schedule.tenant_id,
            env=base_schedule.env,
            slots=offset_slots,
            conflicts=conflicts,
            timeline_tasks=offset_tasks,
            total_slots=len(offset_slots),
            date_range_start=base_schedule.date_range_start,
            date_range_end=max(base_schedule.date_range_end, max([s.scheduled_date for s in offset_slots] or [base_schedule.date_range_end])),
            meta={
                **base_schedule.meta,
                "anchor_channel": anchor_channel.value,
                "channel_offsets": {k.value: v for k, v in offsets_to_apply.items()},
                "is_offset_applied": True,
            },
        )
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _select_pools(self, request: ScheduleRequest) -> List[ContentPool]:
        """Select pools for scheduling."""
        if request.pool_ids:
            return [self.get_pool(pid) for pid in request.pool_ids if self.get_pool(pid)]
        # Default: all pools for tenant/env with matching content types
        all_pools = self.list_pools(request.tenant_id, request.env)
        return [
            p for p in all_pools
            if not request.content_types or p.content_type in request.content_types
        ]
    
    def _select_assets(self, request: ScheduleRequest, pools: List[ContentPool]) -> List[CadenceAsset]:
        """Select assets for scheduling."""
        all_assets = self.list_assets(request.tenant_id, request.env)
        
        # Filter by specified asset IDs if provided
        if request.asset_ids:
            all_assets = [a for a in all_assets if a.asset_id in request.asset_ids]
        
        # Filter by pool if specified
        pool_ids = {p.pool_id for p in pools}
        if pool_ids:
            all_assets = [a for a in all_assets if a.pool_id in pool_ids]
        
        # Filter by content type if specified
        if request.content_types:
            all_assets = [a for a in all_assets if a.content_type in request.content_types]
        
        # Filter by channel if specified
        if request.channels:
            all_assets = [
                a for a in all_assets
                if any(ch in a.channels for ch in request.channels)
            ]
        
        return all_assets
    
    def _create_timeline_task(
        self,
        request: ScheduleRequest,
        slot: ScheduleSlot,
        asset: CadenceAsset,
        pool: Optional[ContentPool],
        offset_days: int = 0,
    ) -> TimelineTask:
        """Create a timeline_core-compatible task from a slot."""
        task_date = slot.scheduled_date + timedelta(days=offset_days)
        
        task_id = generate_deterministic_task_id(
            request.tenant_id,
            request.env,
            request.request_id,
            asset.asset_id,
            slot.channel,
            slot.scheduled_date,
            offset_days=offset_days,
        )
        
        return TimelineTask(
            id=task_id,
            tenant_id=request.tenant_id,
            env=request.env,
            request_id=request.request_id,
            title=f"{slot.content_type.value} on {slot.channel.value}",
            start_date=task_date,
            lane=slot.channel.value,
            tags=[slot.content_type.value, slot.pool_id],
            source_id=asset.asset_id,
            meta={
                "asset_id": asset.asset_id,
                "pool_id": slot.pool_id,
                "content_type": slot.content_type.value,
                "channel": slot.channel.value,
            },
        )
