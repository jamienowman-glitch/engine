
import pytest
from engines.scene_engine.core.geometry import Vector3, Transform, EulerAngles
from engines.scene_engine.core.scene_v2 import SceneV2, SceneNodeV2
from engines.scene_engine.editor.history import HistoryStack
from engines.scene_engine.editor.tools import EditorContext, MoveNodeCommand, MoveTool
from engines.scene_engine.editor.snapping import snap_to_grid

def test_history_undo_redo():
    # Setup Scene
    node = SceneNodeV2(
        id="n1", 
        transform=Transform(
            position=Vector3(x=0,y=0,z=0), 
            rotation=EulerAngles(x=0,y=0,z=0), 
            scale=Vector3(x=1,y=1,z=1)
        )
    )
    scene = SceneV2(id="s1", nodes=[node])
    ctx = EditorContext(scene)
    
    # 1. Move +X 10
    cmd = MoveNodeCommand(ctx, "n1", Vector3(x=10, y=0, z=0))
    ctx.history.push_and_execute(cmd)
    
    assert ctx.scene.nodes[0].transform.position.x == 10.0
    
    # 2. Undo
    ctx.history.undo()
    assert ctx.scene.nodes[0].transform.position.x == 0.0
    
    # 3. Redo
    ctx.history.redo()
    assert ctx.scene.nodes[0].transform.position.x == 10.0

def test_move_tool():
    node = SceneNodeV2(
        id="n1", 
        transform=Transform(
            position=Vector3(x=0,y=0,z=0), 
            rotation=EulerAngles(x=0,y=0,z=0), 
            scale=Vector3(x=1,y=1,z=1)
        )
    )
    scene = SceneV2(id="s1", nodes=[node])
    ctx = EditorContext(scene)
    ctx.selection.add("n1")
    
    tool = MoveTool()
    tool.on_drag(ctx, Vector3(x=1, y=0, z=0))
    tool.on_drag(ctx, Vector3(x=1, y=0, z=0))
    # Accumulated 2.0
    
    tool.apply(ctx)
    
    # Should be at 2.0
    assert ctx.scene.nodes[0].transform.position.x == 2.0
    
    # Undo via context history
    ctx.history.undo()
    assert ctx.scene.nodes[0].transform.position.x == 0.0

def test_snap_to_grid():
    v = Vector3(x=1.1, y=2.9, z=0.0)
    snapped = snap_to_grid(v, step=1.0)
    
    assert snapped.x == 1.0
    assert snapped.y == 3.0
    assert snapped.z == 0.0
