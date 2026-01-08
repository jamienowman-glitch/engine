import os
import pytest
import sys
import asyncio
import inspect
from unittest.mock import MagicMock, patch
from engines.common.identity import RequestContext
from engines.workbench.dynamic_loader import loader, ENGINES_DIR
from engines.mcp_gateway.inventory import get_inventory

@pytest.fixture
def clean_inventory_and_loader():
    inv = get_inventory()
    inv._tools = {}
    
    with patch.dict(os.environ, {"ENABLED_MUSCLES": "video_timeline,video_render"}):
        yield
    
    inv._tools = {}

@pytest.fixture
def mock_timeline_service():
    with patch("engines.muscle.video_timeline.service.get_timeline_service") as m:
        svc = MagicMock()
        m.return_value = svc
        yield svc

@pytest.fixture
def mock_render_service():
    with patch("engines.muscle.video_render.service.get_render_service") as m:
        svc = MagicMock()
        m.return_value = svc
        yield svc

def test_video_wrappers_discovery(clean_inventory_and_loader):
    async def run():
        loader.load_all()
        inv = get_inventory()
        
        tools = inv.list_tools()
        tool_ids = [t.id for t in tools]
        assert "video_timeline" in tool_ids
        assert "video_render" in tool_ids
    
    asyncio.run(run())

def test_video_timeline_read_open(clean_inventory_and_loader, mock_timeline_service):
    async def run():
        loader.load_all()
        inv = get_inventory()
        tool = inv.get_tool("video_timeline")
        scope = tool.scopes["video.timeline.read"]
        
        # Patch GateChain in the dynamic module via globals
        mock_gc = MagicMock()
        scope.handler.__globals__["GateChain"] = MagicMock(return_value=mock_gc)
        
        # Mock Service Data
        mock_timeline_service.get_project.return_value = {"id": "p1"}
        
        # Input
        InputModel = scope.input_model
        args = InputModel(operation="get_project", project_id="p1")
        ctx = RequestContext(tenant_id="t_demo", user_id="u1")
        
        # Run
        res = await scope.handler(ctx, args)
        assert res == {"id": "p1"}
        mock_timeline_service.get_project.assert_called_with("p1")
        
        # Verify GateChain call (Policy Open)
        mock_gc.run.assert_called_with(ctx, action="video.timeline.read", subject_id="p1", subject_type="video_project", surface="video_timeline")
    
    asyncio.run(run())

def test_video_render_submit_policy_enforcement(clean_inventory_and_loader, mock_render_service):
    async def run():
        loader.load_all()
        inv = get_inventory()
        tool = inv.get_tool("video_render")
        scope = tool.scopes["video.render.submit"]
        
        # Patch GateChain in the dynamic module
        mock_gc = MagicMock()
        scope.handler.__globals__["GateChain"] = MagicMock(return_value=mock_gc)
        
        # Input
        InputModel = scope.input_model
        args = InputModel(
            project_id="p1", 
            render_profile="preview_720p_fast", 
            tenant_id="t_demo", 
            env="dev",
            overlap_ms=0.0
        )
        ctx = RequestContext(tenant_id="t_demo", user_id="u1")

        # TEST 1: GateChain throws error (Policy Blocked)
        mock_gc.run.side_effect = Exception("Policy Blocked")
        
        with pytest.raises(Exception, match="Policy Blocked"):
            await scope.handler(ctx, args)
            
        mock_gc.run.assert_called_with(ctx, action="video.render.submit", subject_id="p1", subject_type="video_project", surface="video_render")
        
        # TEST 2: GateChain passes (Policy Allowed/Open)
        mock_gc.run.side_effect = None
        mock_render_service.create_job.return_value = {"id": "job1"}
        
        res = await scope.handler(ctx, args)
        assert res == {"id": "job1"}
    
    asyncio.run(run())

