import pytest
from unittest.mock import MagicMock
from engines.video_batch_render.service import BatchRenderService
from engines.video_batch_render.models import BatchRenderRequest, RenderProfile

def test_batch_execution():
    mock_render = MagicMock()
    # Mock submit_job to return a fake artifact ID
    mock_render.submit_job.side_effect = lambda project_id, width, height, codec: f"art_{width}x{height}"
    
    svc = BatchRenderService(render_service=mock_render)
    
    req = BatchRenderRequest(
        project_id="p1",
        profiles=[
            RenderProfile(width=1920, height=1080, label="Landscape"),
            RenderProfile(width=1080, height=1920, label="Vertical")
        ]
    )
    
    res = svc.execute_batch(req)
    
    # Assert calls
    assert mock_render.submit_job.call_count == 2
    
    # Assert results
    assert res.artifacts["Landscape"] == "art_1920x1080"
    assert res.artifacts["Vertical"] == "art_1080x1920"
    
def test_batch_planning():
    mock_render = MagicMock()
    svc = BatchRenderService(render_service=mock_render)
    
    req = BatchRenderRequest(
        project_id="p1",
        profiles=[RenderProfile(width=1280, height=720, label="HD")]
    )
    
    plan = svc.plan_batch(req)
    assert "HD" in plan.plans
    assert plan.plans["HD"]["width"] == 1280
