"""Tests for Param Graph binding to Avatar Style (P3)."""

from engines.scene_engine.core.scene_v2 import SceneNodeV2, SceneV2
from engines.scene_engine.params.models import (
    ParamBinding,
    ParamGraph,
    ParamNode,
    ParamNodeKind,
    ParamTargetKind,
    ParamType,
)
from engines.scene_engine.params.service import apply_param_bindings, evaluate_param_graph


from engines.scene_engine.core.geometry import Transform, Vector3, Quaternion

def test_param_binding_updates_avatar_style_meta():
    # 1. Setup Scene with Avatar Metadata
    scene = SceneV2(
        id="scene_1",
        nodes=[
            SceneNodeV2(
                id="root", 
                name="AvatarRoot",
                transform=Transform(
                    position=Vector3(x=0,y=0,z=0),
                    rotation=Quaternion(x=0,y=0,z=0,w=1),
                    scale=Vector3(x=1,y=1,z=1)
                ),
                meta={"style_params": {"height": 1.8, "body_build": "average"}}
            )
        ]
    )
    
    # 2. Setup Graph: Input "HeightSlider" -> Output "final_height"
    graph = ParamGraph(
        id="graph_1",
        nodes=[
            ParamNode(id="node_in", kind=ParamNodeKind.INPUT, params={"default": 1.8})
        ],
        exposed_inputs={"HeightSlider": "node_in"},
        outputs={"final_height": "node_in"}
    )
    
    # 3. Setup Binding: final_height -> AVATAR_STYLE_FIELD (height)
    binding = ParamBinding(
        id="bind_1",
        graph_output_name="final_height",
        target_kind=ParamTargetKind.AVATAR_STYLE_FIELD,
        target_id="avatar_root", # ID not strictly used by my logic if I assume root[0], but good practice
        field_name="height"
    )
    
    # 4. Evaluate & Apply
    # Input override: 2.5
    results = evaluate_param_graph(graph, {"HeightSlider": 2.5})
    
    scene = apply_param_bindings(scene, results, [binding])
    
    # 5. Verify Metadata Updated
    root = scene.nodes[0]
    assert root.meta["style_params"]["height"] == 2.5
    assert root.meta.get("dirty_style") is True
