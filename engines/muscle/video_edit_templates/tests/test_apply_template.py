import pytest
from unittest.mock import MagicMock, patch
from engines.video_edit_templates.models import EditTemplate, TrackBlueprint, ClipBlueprint, TemplateSlot
from engines.video_edit_templates.service import TemplateService
from engines.video_edit_templates.registry import TemplateRegistry
from engines.video_timeline.models import VideoProject, Sequence
from engines.media_v2.models import MediaAsset

@patch("engines.video_edit_templates.service.get_timeline_service")
@patch("engines.video_edit_templates.service.get_media_service")
def test_apply_template(mock_media_svc, mock_tl_svc):
    # Setup Registry with a template
    registry = TemplateRegistry()
    t = EditTemplate(
        id="tpl1", name="Simple",
        slots=[TemplateSlot(id="slot1", description="Intro"), TemplateSlot(id="slot2", description="Main")],
        tracks=[
            TrackBlueprint(
                kind="video",
                clips=[
                    ClipBlueprint(slot_id="slot1", start_ms=0, duration_ms=5000),
                    ClipBlueprint(slot_id="slot2", start_ms=5000, duration_ms=5000)
                ]
            )
        ]
    )
    registry.register(t)
    
    # Setup Mocks
    mock_media = mock_media_svc.return_value
    a1 = MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", duration_ms=10000, source_uri="/tmp/a1.mp4")
    a2 = MediaAsset(id="a2", tenant_id="t1", env="dev", kind="video", duration_ms=3000, source_uri="/tmp/a2.mp4") # Short asset
    
    def get_asset_se(aid):
        if aid == "a1": return a1
        if aid == "a2": return a2
        return None
    mock_media.get_asset.side_effect = get_asset_se
    
    mock_tl = mock_tl_svc.return_value
    mock_tl.get_project.return_value = VideoProject(id="p1", tenant_id="t1", env="dev", title="P1")
    
    # Capture creations
    created_clips = []
    def create_clip(c):
        created_clips.append(c)
    mock_tl.create_clip.side_effect = create_clip
    
    # Service
    svc = TemplateService(registry=registry, timeline_service=mock_tl, media_service=mock_media)
    
    # Apply
    # slot1 -> a1 (10s > 5s requested -> should be 5s)
    # slot2 -> a2 (3s < 5s requested -> should be 3s)
    assets_map = {"slot1": "a1", "slot2": "a2"}
    
    seq = svc.apply_template("tpl1", "p1", assets_map)
    
    assert seq.name == "Simple Edit"
    
    # Verify Clips
    assert len(created_clips) == 2
    c1 = created_clips[0]
    c2 = created_clips[1]
    
    # Check C1
    assert c1.asset_id == "a1"
    assert c1.start_ms_on_timeline == 0
    assert (c1.out_ms - c1.in_ms) == 5000
    
    # Check C2
    assert c2.asset_id == "a2"
    assert c2.start_ms_on_timeline == 5000
    assert (c2.out_ms - c2.in_ms) == 3000 # Clamped to asset duration
