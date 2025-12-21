import pytest
from engines.effect_graph.models import EffectGraph, EffectNode
from engines.effect_graph.compiler import GraphCompiler

def test_compiler_linear():
    # Source -> Color -> Blur -> Output
    g = EffectGraph(output_node_id="out1")
    
    n_src = EffectNode(id="src1", type="source", params={"input_index": 0})
    n_color = EffectNode(id="col1", type="color", inputs=["src1"], params={"saturation": 1.5})
    n_blur = EffectNode(id="blur1", type="blur", inputs=["col1"], params={"luma_radius": 5})
    n_out = EffectNode(id="out1", type="output", inputs=["blur1"])
    
    g.add_node(n_src)
    g.add_node(n_color)
    g.add_node(n_blur)
    g.add_node(n_out)
    
    compiler = GraphCompiler()
    result = compiler.compile(g)
    
    # Check syntax roughly
    assert "null" in result
    assert "eq=brightness=0.0:contrast=1.0:saturation=1.5" in result
    assert "boxblur=luma_radius=5" in result
    # Check connectivity
    # src -> eq -> blur -> null
    
def test_compiler_branching():
    # Source -> Split -> (Color, Blur) -> Overlay -> Output
    g = EffectGraph(output_node_id="out1")
    
    n_src = EffectNode(id="src1", type="source", params={"input_index": 0})
    n_split = EffectNode(id="split1", type="split", inputs=["src1"], params={"count": 2})
    
    # Branch 1: Color
    n_color = EffectNode(id="col1", type="color", inputs=["split1"], params={"contrast": 1.2})
    
    # Branch 2: Blur
    n_blur = EffectNode(id="blur1", type="blur", inputs=["split1"], params={"luma_radius": 10})
    
    # Join: Overlay (col=bg, blur=fg)
    n_overlay = EffectNode(id="ov1", type="overlay", inputs=["col1", "blur1"], params={"x": 10, "y": 10})
    
    n_out = EffectNode(id="out1", type="output", inputs=["ov1"])
    
    g.add_node(n_src)
    g.add_node(n_split)
    g.add_node(n_color)
    g.add_node(n_blur)
    g.add_node(n_overlay)
    g.add_node(n_out)
    
    compiler = GraphCompiler()
    result = compiler.compile(g)
    
    assert "split=2" in result
    assert "eq=" in result
    assert "boxblur=" in result
    assert "overlay=x=10:y=10" in result
    
def test_compiler_cycle():
    g = EffectGraph(output_node_id="n1")
    n1 = EffectNode(id="n1", type="color", inputs=["n2"])
    n2 = EffectNode(id="n2", type="color", inputs=["n1"])
    g.add_node(n1)
    g.add_node(n2)
    
    compiler = GraphCompiler()
    with pytest.raises(ValueError, match="Cycle detected"):
        compiler.compile(g)
