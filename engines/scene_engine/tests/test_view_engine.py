"""Tests for View Engine (Level B)."""
from engines.scene_engine.core.geometry import (
    BoxParams,
    EulerAngles,
    Transform,
    Vector3,
)
from engines.scene_engine.core.primitives import build_box_mesh
from engines.scene_engine.core.scene_v2 import SceneNodeV2, SceneV2
from engines.scene_engine.core.types import Camera
from engines.scene_engine.view.models import (
    PickNodeRequest,
    ViewAnalysisRequest,
    ViewportSpec,
)
from engines.scene_engine.view.service import analyze_view, pick_node


def _make_simple_scene() -> SceneV2:
    # 1x1x1 Box at Origin
    mesh = build_box_mesh(BoxParams(width=1, height=1, depth=1))
    
    node = SceneNodeV2(
        id="box1",
        transform=Transform(
            position=Vector3(x=0, y=0, z=0),
            rotation=EulerAngles(x=0, y=0, z=0),
            scale=Vector3(x=1, y=1, z=1)
        ),
        mesh_id=mesh.id
    )
    
    return SceneV2(
        id="scene1",
        nodes=[node],
        meshes=[mesh],
        materials=[],
        # camera=None
    )


def test_analyze_view_sanity():
    scene = _make_simple_scene()
    
    # Cam at (0,0,5) looking at (0,0,0) -> Box should be visible
    viewport = ViewportSpec(
        camera_position=Vector3(x=0, y=0, z=5),
        camera_target=Vector3(x=0, y=0, z=0),
        fov_y_degrees=60.0,
        aspect_ratio=1.0,
        screen_width=100,
        screen_height=100
    )
    
    req = ViewAnalysisRequest(scene=scene, viewport=viewport)
    res = analyze_view(req)
    
    assert len(res.nodes) == 1
    info = res.nodes[0]
    assert info.node_id == "box1"
    assert info.visible == True
    assert info.screen_area_fraction > 0
    
    # BBox check: center should be near 0.5, 0.5
    bbox = info.screen_bbox
    center_x = (bbox[0] + bbox[2]) / 2.0
    center_y = (bbox[1] + bbox[3]) / 2.0
    assert 0.4 < center_x < 0.6
    assert 0.4 < center_y < 0.6


def test_off_screen_culling():
    scene = _make_simple_scene()
    
    # Cam looking away or box is far
    # Box at origin. Cam at (0,0,5). Look at (0,0,-5) [Behind box? No, box is at 0]
    # Look at (100, 0, 0)
    
    viewport = ViewportSpec(
        camera_position=Vector3(x=0, y=0, z=5),
        camera_target=Vector3(x=100, y=0, z=5), # Look Right
        fov_y_degrees=60.0,
        aspect_ratio=1.0,
        screen_width=100,
        screen_height=100
    )
    
    res = analyze_view(ViewAnalysisRequest(scene=scene, viewport=viewport))
    info = res.nodes[0]
    assert info.visible == False


def test_picking_hit():
    scene = _make_simple_scene()
    viewport = ViewportSpec(
        camera_position=Vector3(x=0, y=0, z=5),
        camera_target=Vector3(x=0, y=0, z=0),
        fov_y_degrees=60.0,
        aspect_ratio=1.0,
        screen_width=100,
        screen_height=100
    )
    
    # Pick center
    req = PickNodeRequest(
        scene=scene, 
        viewport=viewport, 
        screen_x=0.5, 
        screen_y=0.5
    )
    res = pick_node(req)
    
    assert res.node_id == "box1"
    assert res.hit_position is not None
    # Hit should be front face of box at z=0.5
    # Box is width 1, centered at 0. Extends -0.5 to 0.5.
    # Cam at +5. Ray goes +z to -z (cam looks at 0).
    # First hit is z=0.5
    assert abs(res.hit_position.z - 0.5) < 0.01


def test_picking_miss():
    scene = _make_simple_scene()
    viewport = ViewportSpec(
        camera_position=Vector3(x=0, y=0, z=5),
        camera_target=Vector3(x=0, y=0, z=0),
        fov_y_degrees=60.0,
        aspect_ratio=1.0,
        screen_width=100,
        screen_height=100
    )
    
    # Pick corner (0,0) -> likely empty space if FOV 60
    req = PickNodeRequest(scene=scene, viewport=viewport, screen_x=0.0, screen_y=0.0)
    res = pick_node(req)
    
    assert res.node_id is None
