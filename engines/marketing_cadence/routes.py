"""
Marketing Cadence Routes.

HTTP endpoints for pool/asset management and schedule generation.
"""

from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Body

from engines.marketing_cadence.models import (
    ContentPool,
    CadenceAsset,
    ChannelType,
    ContentType,
    ScheduleRequest,
)
from engines.marketing_cadence.service import CadenceService


# Global service instance
_service = CadenceService()


router = APIRouter(prefix="/api/cadence", tags=["cadence"])


# ============================================================================
# Utility Functions
# ============================================================================

def _validate_context(payload: Dict[str, Any]) -> tuple[str, str]:
    """Extract and validate tenant_id and env from payload."""
    tenant_id = payload.get("tenant_id")
    env = payload.get("env")
    if not tenant_id or not env:
        raise HTTPException(status_code=400, detail="tenant_id and env are required")
    return tenant_id, env


# ============================================================================
# Pool CRUD Endpoints
# ============================================================================

@router.post("/pools/register")
def register_pool(payload: Dict[str, Any] = Body(...)):
    """Register a new content pool."""
    try:
        tenant_id, env = _validate_context(payload)
    except HTTPException:
        raise
    
    pool_data = {
        "pool_id": payload.get("pool_id"),
        "tenant_id": tenant_id,
        "env": env,
        "content_type": payload.get("content_type"),
        "channels": payload.get("channels", []),
        "min_days_between_repeats": payload.get("min_days_between_repeats", 0),
        "tags": payload.get("tags", {}),
        "meta": payload.get("meta", {}),
    }
    
    try:
        pool = ContentPool(**pool_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid pool data: {str(e)}")
    
    pool_id = _service.register_pool(pool)
    
    return {
        "status": "success",
        "pool_id": pool_id,
        "message": "Pool registered successfully",
    }


@router.get("/pools/{pool_id}")
def get_pool(pool_id: str):
    """Get a pool by ID."""
    pool = _service.get_pool(pool_id)
    if not pool:
        raise HTTPException(status_code=404, detail=f"Pool {pool_id} not found")
    return pool.model_dump()


@router.get("/pools")
def list_pools(tenant_id: str, env: str):
    """List all pools for a tenant/env."""
    pools = _service.list_pools(tenant_id, env)
    return {
        "status": "success",
        "pools": [p.model_dump() for p in pools],
        "count": len(pools),
    }


# ============================================================================
# Asset CRUD Endpoints
# ============================================================================

@router.post("/assets/register")
def register_asset(payload: Dict[str, Any] = Body(...)):
    """Register a new content asset."""
    try:
        tenant_id, env = _validate_context(payload)
    except HTTPException:
        raise
    
    asset_data = {
        "asset_id": payload.get("asset_id"),
        "tenant_id": tenant_id,
        "env": env,
        "content_type": payload.get("content_type"),
        "pool_id": payload.get("pool_id"),
        "channels": payload.get("channels", []),
        "cooldown_days": payload.get("cooldown_days", 0),
        "tags": payload.get("tags", {}),
        "meta": payload.get("meta", {}),
    }
    
    try:
        asset = CadenceAsset(**asset_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid asset data: {str(e)}")
    
    asset_id = _service.register_asset(asset)
    
    return {
        "status": "success",
        "asset_id": asset_id,
        "message": "Asset registered successfully",
    }


@router.get("/assets/{asset_id}")
def get_asset(asset_id: str):
    """Get an asset by ID."""
    asset = _service.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")
    return asset.model_dump()


@router.get("/assets")
def list_assets(tenant_id: str, env: str, pool_id: Optional[str] = None):
    """List assets for a tenant/env, optionally filtered by pool."""
    if pool_id:
        assets = _service.list_assets_by_pool(pool_id)
    else:
        assets = _service.list_assets(tenant_id, env)
    
    return {
        "status": "success",
        "assets": [a.model_dump() for a in assets],
        "count": len(assets),
    }


# ============================================================================
# Schedule Generation Endpoints
# ============================================================================

@router.post("/schedule/generate")
def generate_schedule(payload: Dict[str, Any] = Body(...)):
    """Generate a schedule respecting all cooldowns and caps (MC01)."""
    try:
        tenant_id, env = _validate_context(payload)
    except HTTPException:
        raise
    
    request_data = {
        "request_id": payload.get("request_id"),
        "tenant_id": tenant_id,
        "env": env,
        "start_date": payload.get("start_date"),
        "end_date": payload.get("end_date"),
        "pool_ids": payload.get("pool_ids", []),
        "asset_ids": payload.get("asset_ids", []),
        "channels": payload.get("channels", []),
        "content_types": payload.get("content_types", []),
        "global_daily_cap_soft": payload.get("global_daily_cap_soft"),
        "global_daily_cap_hard": payload.get("global_daily_cap_hard"),
        "channel_caps": payload.get("channel_caps", {}),
        "anchor_channel": payload.get("anchor_channel"),
        "channel_offsets": payload.get("channel_offsets", {}),
        "meta": payload.get("meta", {}),
    }
    
    try:
        request = ScheduleRequest(**request_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
    
    try:
        suggestion = _service.generate_schedule(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schedule generation failed: {str(e)}")
    
    return {
        "status": "success",
        "schedule": suggestion.model_dump(),
    }


@router.post("/schedule/apply-offsets")
def apply_offsets(payload: Dict[str, Any] = Body(...)):
    """Apply anchor + offsets to a base schedule (MC02)."""
    try:
        tenant_id, env = _validate_context(payload)
    except HTTPException:
        raise
    
    # Get the base schedule (or regenerate it)
    base_request_data = {
        "request_id": payload.get("request_id"),
        "tenant_id": tenant_id,
        "env": env,
        "start_date": payload.get("start_date"),
        "end_date": payload.get("end_date"),
        "pool_ids": payload.get("pool_ids", []),
        "asset_ids": payload.get("asset_ids", []),
        "channels": payload.get("channels", []),
        "content_types": payload.get("content_types", []),
        "global_daily_cap_soft": payload.get("global_daily_cap_soft"),
        "global_daily_cap_hard": payload.get("global_daily_cap_hard"),
        "channel_caps": payload.get("channel_caps", {}),
        "meta": payload.get("meta", {}),
    }
    
    try:
        base_request = ScheduleRequest(**base_request_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
    
    # Generate base schedule
    try:
        base_schedule = _service.generate_schedule(base_request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Base schedule generation failed: {str(e)}")
    
    # Extract anchor + offsets
    anchor_channel_str = payload.get("anchor_channel")
    if not anchor_channel_str:
        raise HTTPException(status_code=400, detail="anchor_channel is required")
    
    try:
        anchor_channel = ChannelType(anchor_channel_str)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid anchor_channel: {anchor_channel_str}")
    
    channel_offsets_raw = payload.get("channel_offsets", {})
    channel_offsets = {}
    for ch_str, offset in channel_offsets_raw.items():
        try:
            ch = ChannelType(ch_str)
            channel_offsets[ch] = int(offset)
        except (ValueError, TypeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid channel offset: {str(e)}")
    
    # Apply offsets
    try:
        offset_schedule = _service.apply_offsets(base_schedule, anchor_channel, channel_offsets)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Offset application failed: {str(e)}")
    
    return {
        "status": "success",
        "base_schedule": base_schedule.model_dump(),
        "offset_schedule": offset_schedule.model_dump(),
    }
