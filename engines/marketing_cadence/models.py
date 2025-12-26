"""
Marketing Cadence Core Models.

Defines cadence pools, assets, cooldown rules, and schedule structures.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, date, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field, model_validator


# ============================================================================
# Enums
# ============================================================================

class ChannelType(str, Enum):
    """Channel/platform type."""
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    YOUTUBE_SHORTS = "youtube_shorts"
    YOUTUBE_LONGFORM = "youtube_longform"
    EMAIL = "email"
    SMS = "sms"
    DM = "dm"
    FEED_CAROUSEL = "feed_carousel"
    COMMUNITY = "community"
    BLOG = "blog"
    HOMEPAGE = "homepage"
    STORIES = "stories"


class ContentType(str, Enum):
    """Content type."""
    STORIES = "stories"
    SHORT_FORM = "short_form"
    TRIAL_REEL = "trial_reel"
    LONG_FORM = "long_form"
    EMAIL_FLOW = "email_flow"
    EMAIL_BROADCAST = "email_broadcast"
    DM_FLOW = "dm_flow"
    DM_BROADCAST = "dm_broadcast"
    FEED_CAROUSEL = "feed_carousel"
    COMMUNITY_POST = "community_post"
    BLOG = "blog"
    HOMEPAGE_HERO = "homepage_hero"


# ============================================================================
# Cooldown and Cap Rules
# ============================================================================

class CooldownRule(BaseModel):
    """Cooldown/gap rule for pool or asset."""
    min_days_between_repeats: int = Field(default=0, ge=0)
    asset_cooldown_days: Optional[int] = Field(default=None, ge=0)
    
    def __hash__(self):
        return hash((self.min_days_between_repeats, self.asset_cooldown_days))


class ContentTypeDefaults(BaseModel):
    """Default cooldown and cap rules per content type."""
    content_type: ContentType
    pool_min_days_between_repeats: int = Field(default=0, ge=0)
    asset_cooldown_days: int = Field(default=0, ge=0)
    target_per_day_per_channel: int = Field(default=1, ge=0)
    hard_cap_per_day_per_channel: int = Field(default=3, ge=0)
    max_per_week_segment: Optional[int] = Field(default=None, ge=0)  # For broadcasts


# ============================================================================
# Content Pool and Asset
# ============================================================================

class ContentPool(BaseModel):
    """A pool of content assets for a given content type."""
    pool_id: str
    tenant_id: str
    env: str
    content_type: ContentType
    channels: List[ChannelType] = Field(default_factory=list)
    
    # Pool-level cooldown: min days between repeats of assets from this pool
    min_days_between_repeats: int = Field(default=0, ge=0)
    
    tags: Dict[str, Any] = Field(default_factory=dict)
    meta: Dict[str, Any] = Field(default_factory=dict)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    def __hash__(self):
        return hash(self.pool_id)


class CadenceAsset(BaseModel):
    """A single content asset scheduled for distribution."""
    asset_id: str
    tenant_id: str
    env: str
    content_type: ContentType
    pool_id: str
    channels: List[ChannelType] = Field(default_factory=list)
    
    # Asset-level cooldown: min days before this asset can be repeated
    cooldown_days: int = Field(default=0, ge=0)
    
    tags: Dict[str, Any] = Field(default_factory=dict)
    meta: Dict[str, Any] = Field(default_factory=dict)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @model_validator(mode='after')
    def validate_pool_match(self):
        if not self.pool_id:
            raise ValueError("asset must belong to a pool (pool_id required)")
        return self
    
    def __hash__(self):
        return hash(self.asset_id)


# ============================================================================
# Schedule Request and Response
# ============================================================================

class ScheduleSlot(BaseModel):
    """A single scheduled slot for an asset on a channel."""
    slot_id: str
    asset_id: str
    pool_id: str
    content_type: ContentType
    channel: ChannelType
    scheduled_date: date
    priority: int = Field(default=0, ge=0)  # Lower = higher priority
    
    tags: Dict[str, Any] = Field(default_factory=dict)
    meta: Dict[str, Any] = Field(default_factory=dict)


class ConflictReport(BaseModel):
    """Conflict detected in schedule (cooldown, cap, etc)."""
    conflict_type: str  # e.g., "cooldown_violation", "cap_exceeded", "insufficient_assets"
    asset_id: Optional[str] = None
    pool_id: Optional[str] = None
    channel: Optional[ChannelType] = None
    scheduled_date: Optional[date] = None
    message: str
    severity: str = Field(default="warning")  # "warning", "error"


class TimelineTask(BaseModel):
    """A task in timeline_core-compatible format."""
    id: str
    tenant_id: str
    env: str
    request_id: str
    
    title: str
    start_date: date
    
    lane: str  # e.g., channel name
    tags: List[str] = Field(default_factory=list)
    
    source_kind: str = Field(default="cadence_asset")
    source_id: str
    
    meta: Dict[str, Any] = Field(default_factory=dict)


class ScheduleSuggestion(BaseModel):
    """Response from schedule generation."""
    request_id: str
    tenant_id: str
    env: str
    
    # Schedule slots grouped by channel
    slots: List[ScheduleSlot] = Field(default_factory=list)
    
    # Conflicts detected
    conflicts: List[ConflictReport] = Field(default_factory=list)
    
    # Timeline-core compatible tasks
    timeline_tasks: List[TimelineTask] = Field(default_factory=list)
    
    # Metadata
    total_slots: int = Field(default=0)
    date_range_start: date
    date_range_end: date
    
    meta: Dict[str, Any] = Field(default_factory=dict)


class ScheduleRequest(BaseModel):
    """Request for schedule generation."""
    request_id: str
    tenant_id: str
    env: str
    
    # Date range
    start_date: date
    end_date: date
    
    # Which pools/assets to use
    pool_ids: List[str] = Field(default_factory=list)
    asset_ids: List[str] = Field(default_factory=list)
    
    # Which channels/content types to schedule
    channels: List[ChannelType] = Field(default_factory=list)
    content_types: List[ContentType] = Field(default_factory=list)
    
    # Optional overrides for defaults
    global_daily_cap_soft: Optional[int] = Field(default=None, ge=1)
    global_daily_cap_hard: Optional[int] = Field(default=None, ge=1)
    channel_caps: Dict[ChannelType, int] = Field(default_factory=dict)
    
    # Anchor + offsets for MC02 (optional)
    anchor_channel: Optional[ChannelType] = None
    channel_offsets: Dict[ChannelType, int] = Field(default_factory=dict)
    
    meta: Dict[str, Any] = Field(default_factory=dict)
    
    @model_validator(mode='after')
    def validate_dates(self):
        if self.start_date > self.end_date:
            raise ValueError("start_date must be <= end_date")
        return self


# ============================================================================
# Deterministic ID Helpers
# ============================================================================

def generate_deterministic_schedule_id(
    tenant_id: str,
    env: str,
    request_id: str,
) -> str:
    """Generate deterministic ID for schedule."""
    parts = [tenant_id, env, request_id]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def generate_deterministic_slot_id(
    tenant_id: str,
    env: str,
    request_id: str,
    asset_id: str,
    channel: ChannelType,
    scheduled_date: date,
) -> str:
    """Generate deterministic ID for a schedule slot."""
    parts = [
        tenant_id,
        env,
        request_id,
        asset_id,
        channel.value,
        scheduled_date.isoformat(),
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def generate_deterministic_task_id(
    tenant_id: str,
    env: str,
    request_id: str,
    asset_id: str,
    channel: ChannelType,
    scheduled_date: date,
    offset_days: int = 0,
) -> str:
    """Generate deterministic ID for timeline task (with offset support for MC02)."""
    parts = [
        tenant_id,
        env,
        request_id,
        asset_id,
        channel.value,
        (scheduled_date + timedelta(days=offset_days)).isoformat(),
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
