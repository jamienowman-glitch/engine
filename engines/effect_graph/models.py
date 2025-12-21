from __future__ import annotations
import uuid
from typing import Dict, List, Literal, Any, Optional
from pydantic import BaseModel, Field

EffectType = Literal[
    "source",   # Input video
    "output",   # Final output
    "color",    # eq/hue/sat
    "blur",     # boxblur
    "overlay",  # overlay (requires 2 inputs)
    "split",    # split stream
    "text",     # drawtext
]

class EffectNode(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    type: EffectType
    inputs: List[str] = Field(default_factory=list) # IDs of input nodes
    params: Dict[str, Any] = Field(default_factory=dict) # Filter parameters
    
    # Metadata for compiler
    # e.g. "pad_out_count" for split nodes?
    
class EffectGraph(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    nodes: Dict[str, EffectNode] = Field(default_factory=dict)
    output_node_id: str
    
    def add_node(self, node: EffectNode):
        self.nodes[node.id] = node
        
    def get_node(self, node_id: str) -> Optional[EffectNode]:
        return self.nodes.get(node_id)
