"""
Tests for marketing cadence routes.
"""

import pytest
from datetime import date
from fastapi.testclient import TestClient
from fastapi import FastAPI

from engines.marketing_cadence.routes import router
from engines.marketing_cadence.service import CadenceService


# Create a test FastAPI app with the router
app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestPoolRoutes:
    """Test pool management endpoints."""
    
    def test_register_pool_success(self):
        """Successfully register a pool."""
        payload = {
            "pool_id": "pool_001",
            "tenant_id": "tenant_001",
            "env": "dev",
            "content_type": "stories",
            "channels": ["instagram", "stories"],
            "min_days_between_repeats": 3,
        }
        
        response = client.post("/api/cadence/pools/register", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["pool_id"] == "pool_001"
    
    def test_register_pool_missing_tenant(self):
        """Reject pool registration without tenant_id."""
        payload = {
            "pool_id": "pool_001",
            "env": "dev",
            "content_type": "stories",
        }
        
        response = client.post("/api/cadence/pools/register", json=payload)
        
        assert response.status_code == 400
    
    def test_register_pool_missing_env(self):
        """Reject pool registration without env."""
        payload = {
            "pool_id": "pool_001",
            "tenant_id": "tenant_001",
            "content_type": "stories",
        }
        
        response = client.post("/api/cadence/pools/register", json=payload)
        
        assert response.status_code == 400
    
    def test_get_pool_not_found(self):
        """Return 404 for non-existent pool."""
        response = client.get("/api/cadence/pools/nonexistent")
        assert response.status_code == 404
    
    def test_list_pools_empty(self):
        """List pools returns empty list if none exist."""
        response = client.get(
            "/api/cadence/pools",
            params={"tenant_id": "tenant_999", "env": "dev"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["pools"]) == 0


class TestAssetRoutes:
    """Test asset management endpoints."""
    
    def test_register_asset_success(self):
        """Successfully register an asset."""
        payload = {
            "asset_id": "asset_001",
            "tenant_id": "tenant_001",
            "env": "dev",
            "content_type": "short_form",
            "pool_id": "pool_001",
            "channels": ["instagram", "tiktok"],
            "cooldown_days": 14,
        }
        
        response = client.post("/api/cadence/assets/register", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["asset_id"] == "asset_001"
    
    def test_register_asset_missing_pool(self):
        """Reject asset registration without pool_id."""
        payload = {
            "asset_id": "asset_001",
            "tenant_id": "tenant_001",
            "env": "dev",
            "content_type": "short_form",
            "channels": ["instagram"],
        }
        
        response = client.post("/api/cadence/assets/register", json=payload)
        
        assert response.status_code == 400
    
    def test_get_asset_not_found(self):
        """Return 404 for non-existent asset."""
        response = client.get("/api/cadence/assets/nonexistent")
        assert response.status_code == 404
    
    def test_list_assets_empty(self):
        """List assets returns empty list if none exist."""
        response = client.get(
            "/api/cadence/assets",
            params={"tenant_id": "tenant_999", "env": "dev"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["assets"]) == 0


class TestScheduleRoutes:
    """Test schedule generation endpoints."""
    
    def test_generate_schedule_success(self):
        """Successfully generate a schedule."""
        payload = {
            "request_id": "req_001",
            "tenant_id": "tenant_001",
            "env": "dev",
            "start_date": "2025-01-01",
            "end_date": "2025-01-07",
            "pool_ids": [],
            "asset_ids": [],
            "channels": ["instagram"],
            "content_types": ["short_form"],
        }
        
        response = client.post("/api/cadence/schedule/generate", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "schedule" in data
        assert data["schedule"]["request_id"] == "req_001"
    
    def test_generate_schedule_missing_tenant(self):
        """Reject schedule request without tenant_id."""
        payload = {
            "request_id": "req_001",
            "env": "dev",
            "start_date": "2025-01-01",
            "end_date": "2025-01-07",
        }
        
        response = client.post("/api/cadence/schedule/generate", json=payload)
        
        assert response.status_code == 400
    
    def test_generate_schedule_invalid_dates(self):
        """Reject schedule request with invalid dates."""
        payload = {
            "request_id": "req_001",
            "tenant_id": "tenant_001",
            "env": "dev",
            "start_date": "2025-01-07",
            "end_date": "2025-01-01",
        }
        
        response = client.post("/api/cadence/schedule/generate", json=payload)
        
        assert response.status_code == 400
    
    def test_apply_offsets_success(self):
        """Successfully apply offsets to schedule."""
        payload = {
            "request_id": "req_001",
            "tenant_id": "tenant_001",
            "env": "dev",
            "start_date": "2025-01-01",
            "end_date": "2025-01-07",
            "pool_ids": [],
            "asset_ids": [],
            "channels": ["youtube_shorts"],
            "content_types": ["short_form"],
            "anchor_channel": "youtube_shorts",
            "channel_offsets": {
                "instagram": 1,
                "tiktok": 2,
            },
        }
        
        response = client.post("/api/cadence/schedule/apply-offsets", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "base_schedule" in data
        assert "offset_schedule" in data
    
    def test_apply_offsets_missing_anchor(self):
        """Reject offset request without anchor_channel."""
        payload = {
            "request_id": "req_001",
            "tenant_id": "tenant_001",
            "env": "dev",
            "start_date": "2025-01-01",
            "end_date": "2025-01-07",
            "channel_offsets": {"instagram": 1},
        }
        
        response = client.post("/api/cadence/schedule/apply-offsets", json=payload)
        
        assert response.status_code == 400
    
    def test_apply_offsets_invalid_anchor(self):
        """Reject offset request with invalid anchor_channel."""
        payload = {
            "request_id": "req_001",
            "tenant_id": "tenant_001",
            "env": "dev",
            "start_date": "2025-01-01",
            "end_date": "2025-01-07",
            "anchor_channel": "invalid_channel",
            "channel_offsets": {"instagram": 1},
        }
        
        response = client.post("/api/cadence/schedule/apply-offsets", json=payload)
        
        assert response.status_code == 400


class TestEndToEnd:
    """End-to-end workflow tests."""
    
    def test_register_pool_and_asset_then_schedule(self):
        """Full workflow: register pool/asset, then generate schedule."""
        # Register pool
        pool_payload = {
            "pool_id": "pool_e2e",
            "tenant_id": "tenant_e2e",
            "env": "test",
            "content_type": "short_form",
            "channels": ["instagram"],
        }
        pool_response = client.post("/api/cadence/pools/register", json=pool_payload)
        assert pool_response.status_code == 200
        
        # Register asset
        asset_payload = {
            "asset_id": "asset_e2e",
            "tenant_id": "tenant_e2e",
            "env": "test",
            "content_type": "short_form",
            "pool_id": "pool_e2e",
            "channels": ["instagram"],
        }
        asset_response = client.post("/api/cadence/assets/register", json=asset_payload)
        assert asset_response.status_code == 200
        
        # Generate schedule
        schedule_payload = {
            "request_id": "req_e2e",
            "tenant_id": "tenant_e2e",
            "env": "test",
            "start_date": "2025-01-01",
            "end_date": "2025-01-07",
            "pool_ids": ["pool_e2e"],
            "asset_ids": ["asset_e2e"],
            "channels": ["instagram"],
            "content_types": ["short_form"],
        }
        schedule_response = client.post(
            "/api/cadence/schedule/generate", json=schedule_payload
        )
        assert schedule_response.status_code == 200
        
        data = schedule_response.json()
        assert data["status"] == "success"
        assert data["schedule"]["total_slots"] > 0
