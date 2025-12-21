
import pytest
from engines.scene_engine.params.models import (
    ParamGraph, ParamNode, ParamNodeKind, ParamBinding, ParamTargetKind
)
from engines.scene_engine.params.service import evaluate_param_graph, apply_param_bindings
from engines.scene_engine.core.scene_v2 import SceneV2, SceneNodeV2
from engines.scene_engine.core.geometry import Transform, Vector3, EulerAngles

def test_evaluate_simple_graph():
    # Input(En) -> * 2 -> + 1 -> Out
    nodes = [
        ParamNode(id="n_in", kind=ParamNodeKind.INPUT, params={"default": 1.0}),
        ParamNode(id="n_const", kind=ParamNodeKind.CONSTANT, params={"value": 2.0}),
        ParamNode(id="n_mult", kind=ParamNodeKind.MULTIPLY, inputs={"a": "n_in", "b": "n_const"}),
        ParamNode(id="n_add", kind=ParamNodeKind.ADD, inputs={"a": "n_mult"}, params={"b": 1.0}) # b missing input, so default 0? wait, inputs map slot->id. 
        # Add node implementation checks inputs["b"]. If not linked, defaults to 0.0. 
        # But we want to add 1.0. We should make a constant for 1.0 or support literal params in Add?
        # My implementation `_eval_add` reads inputs["b"]. If I want param, I need a CONSTANT node.
    ]
    # Let's fix the ADD node to use a 2nd constant
    nodes.append(ParamNode(id="n_one", kind=ParamNodeKind.CONSTANT, params={"value": 1.0}))
    nodes[-2].inputs["b"] = "n_one" # Link n_add input b to n_one

    graph = ParamGraph(
        id="g1",
        nodes=nodes,
        exposed_inputs={"energy": "n_in"},
        outputs={"result": "n_add"} # n_add ID
    ) # Oops, node[-2] is n_add. Wait, index logic is fragile.
    
    # Re-build cleanly
    n_in = ParamNode(id="n_in", kind=ParamNodeKind.INPUT, params={"default": 0.5})
    n_mul_val = ParamNode(id="c_2", kind=ParamNodeKind.CONSTANT, params={"value": 2.0})
    n_mul = ParamNode(id="op_mul", kind=ParamNodeKind.MULTIPLY, inputs={"a": "n_in", "b": "c_2"})
    n_add_val = ParamNode(id="c_1", kind=ParamNodeKind.CONSTANT, params={"value": 1.0})
    n_add = ParamNode(id="op_add", kind=ParamNodeKind.ADD, inputs={"a": "op_mul", "b": "c_1"})
    
    graph = ParamGraph(
        id="test",
        nodes=[n_in, n_mul_val, n_mul, n_add_val, n_add],
        exposed_inputs={"energy": "n_in"},
        outputs={"final": "op_add"}
    )
    
    # Eval with energy = 0.5 -> (0.5 * 2) + 1 = 2.0
    res = evaluate_param_graph(graph, {"energy": 0.5})
    assert abs(res["final"] - 2.0) < 1e-6
    
    # Eval with energy = 3 -> (3 * 2) + 1 = 7.0
    res = evaluate_param_graph(graph, {"energy": 3.0})
    assert abs(res["final"] - 7.0) < 1e-6

def test_apply_bindings():
    scene = SceneV2(
        id="s1", 
        nodes=[
            SceneNodeV2(
                id="node_a", 
                transform=Transform(
                    position=Vector3(x=0, y=0, z=0),
                    rotation=EulerAngles(x=0,y=0,z=0),
                    scale=Vector3(x=1,y=1,z=1)
                )
            )
        ]
    )
    
    results = {"my_scale": 2.5}
    
    bindings = [
        ParamBinding(
            id="b1",
            graph_output_name="my_scale",
            target_kind=ParamTargetKind.NODE_SCALE_UNIFORM,
            target_id="node_a"
        )
    ]
    
    apply_param_bindings(scene, results, bindings)
    

    assert abs(scene.nodes[0].transform.scale.x - 2.5) < 1e-6

def test_param_list_matching():
    # Test ADD with two lists
    # A = [1, 2]
    # B = [10, 20]
    # Expected = [11, 22]
    
    # helper check
    from engines.scene_engine.params.service import _eval_add
    
    res = _eval_add({"a": [1.0, 2.0], "b": [10.0, 20.0]})
    assert isinstance(res, list)
    assert res == [11.0, 22.0]
    
    # Test Mismatch (Longest list)
    # A = [1]
    # B = [10, 20]
    # Expected = [11, 21] (1 repeats)
    res2 = _eval_add({"a": [1.0], "b": [10.0, 20.0]})
    assert res2 == [11.0, 21.0]

def test_param_grid_generator():
    from engines.scene_engine.params.service import _eval_grid_2d
    from engines.scene_engine.core.geometry import Vector3
    
    # 2x2 grid, width 10, height 10.
    # Start -5, -5. Step 10.
    # Points: (-5,0,-5), (5,0,-5), (-5,0,5), (5,0,5)
    
    pts = _eval_grid_2d({"width": 10, "height": 10, "count_x": 2, "count_y": 2})
    assert len(pts) == 4
    assert isinstance(pts[0], Vector3)
    
    assert pts[0].x == -5.0
    assert pts[3].x == 5.0

def test_param_graph_v2_full():
    """
    Test a graph:
    Grid -> Noise -> Move Y
    """
    from engines.scene_engine.params.models import ParamGraph, ParamNode, ParamNodeKind
    from engines.scene_engine.params.service import evaluate_param_graph
    
    # Nodes
    # 1. Grid Generator
    n_grid = ParamNode(
        id="grid", 
        kind=ParamNodeKind.GRID_2D, 
        params={"width": 10, "height": 10, "count_x": 3, "count_y": 1} # 3 points in line
    )
    # Pts: (-5,0,-5), (0,0,-5), (5,0,-5) approximately? 
    
    # 2. Random Float -> Add
    n_rnd = ParamNode(
        id="rnd",
        kind=ParamNodeKind.RANDOM_FLOAT,
        params={"count": 3, "min": 0, "max": 1, "seed": 42}
    )
    
    n_rnd2 = ParamNode(
        id="rnd2",
        kind=ParamNodeKind.RANDOM_FLOAT,
        params={"count": 3, "min": 10, "max": 11, "seed": 99}
    )
    
    n_add_f = ParamNode(
        id="add_f",
        kind=ParamNodeKind.ADD,
        inputs={"a": "rnd", "b": "rnd2"}
    )
    
    graph = ParamGraph(
        id="g_test",
        nodes=[n_grid, n_rnd, n_rnd2, n_add_f],
        outputs={"final": "add_f", "grid_out": "grid"}
    )
    
    res = evaluate_param_graph(graph, {})
    
    assert len(res["final"]) == 3
    assert len(res["grid_out"]) == 3

