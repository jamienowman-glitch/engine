from typing import List, Dict, Set, Tuple
from engines.effect_graph.models import EffectGraph, EffectNode

class GraphCompiler:
    def __init__(self):
        self.pad_counter = 0

    def _get_next_pad(self) -> str:
        self.pad_counter += 1
        return f"v{self.pad_counter}"

    def compile(self, graph: EffectGraph) -> str:
        # Simple compilation strategy: Topological sort.
        # 1. Build adjacency list
        node_ids = list(graph.nodes.keys())
        adj: Dict[str, List[str]] = {nid: [] for nid in node_ids} # node -> outputs
        in_degree: Dict[str, int] = {nid: 0 for nid in node_ids}
        
        for nid, node in graph.nodes.items():
            for inp_id in node.inputs:
                if inp_id in adj:
                    adj[inp_id].append(nid)
                    in_degree[nid] += 1
        
        # 2. Kahn's Algo for sort
        queue = [nid for nid in node_ids if in_degree[nid] == 0]
        sorted_nodes: List[str] = []
        
        while queue:
            nid = queue.pop(0)
            sorted_nodes.append(nid)
            for neighbor in adj[nid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
                    
        if len(sorted_nodes) != len(node_ids):
            raise ValueError("Cycle detected in Effect Graph")
            
        # 3. Generate Filters
        # We need to track output pads of each node
        node_outputs: Dict[str, List[str]] = {} # node_id -> [pad_name]
        filters: List[str] = []
        
        # Initialize sources
        # We assume source nodes map to external inputs [0:v], [1:v] etc.
        # Typically the 'source' node in graph should specify which external input index it uses.
        # But for now let's assume params['input_index'] or similar.
        
        for nid in sorted_nodes:
            node = graph.nodes[nid]
            
            # Resolve Input Pads
            input_pads = []
            if node.type != "source":
                for inp_id in node.inputs:
                    # Consume one output from the input node
                    if not node_outputs.get(inp_id):
                        raise ValueError(f"Node {nid} input {inp_id} has no available outputs")
                    pad = node_outputs[inp_id].pop(0)
                    input_pads.append(f"[{pad}]")
            
            output_pad = self._get_next_pad()
            filter_str = ""
            
            if node.type == "source":
                # Source node passes through an external input stream
                idx = node.params.get("input_index", 0)
                # We rename [idx:v] to our internal pad
                # Use `null` filter or `copy`? Usually `null` is safe pass-through.
                source_label = f"{idx}:v"
                filter_str = f"[{source_label}]null[{output_pad}]"
                node_outputs[nid] = [output_pad]
                
            elif node.type == "color":
                # eq filter
                # params: brightness, contrast, saturation
                b = node.params.get("brightness", 0.0)
                c = node.params.get("contrast", 1.0)
                s = node.params.get("saturation", 1.0)
                f_args = f"brightness={b}:contrast={c}:saturation={s}"
                filter_str = f"{''.join(input_pads)}eq={f_args}[{output_pad}]"
                node_outputs[nid] = [output_pad]
                
            elif node.type == "blur":
                # boxblur
                # params: luma_radius, luma_power
                lr = node.params.get("luma_radius", 2)
                lp = node.params.get("luma_power", 1)
                filter_str = f"{''.join(input_pads)}boxblur=luma_radius={lr}:luma_power={lp}[{output_pad}]"
                node_outputs[nid] = [output_pad]
                
            elif node.type == "overlay":
                # requires 2 inputs
                if len(input_pads) < 2:
                    raise ValueError(f"Overlay node {nid} requires 2 inputs")
                x = node.params.get("x", 0)
                y = node.params.get("y", 0)
                # overlay=x=...:y=...
                # Note: inputs[0] is background, inputs[1] is foreground
                filter_str = f"{input_pads[0]}{input_pads[1]}overlay=x={x}:y={y}[{output_pad}]"
                node_outputs[nid] = [output_pad]
                
            elif node.type == "split":
                # splits input into N copies
                count = node.params.get("count", 2)
                out_pads = [self._get_next_pad() for _ in range(count)]
                joined_outs = "".join([f"[{p}]" for p in out_pads])
                filter_str = f"{''.join(input_pads)}split={count}{joined_outs}"
                node_outputs[nid] = out_pads
                # We return here because we don't use single 'output_pad' variable
                filters.append(filter_str)
                continue 
                
            elif node.type == "output":
                # Output node just sinks result to a final known label, e.g. [out]?
                # Or just produces a pad that caller uses.
                # In this system let's just use `null`.
                # Compiler usually returns the full string.
                # If this is the DAG Output, we might want to ensure it ends up at a specific label.
                # But let's just pass it through.
                filter_str = f"{''.join(input_pads)}null[{output_pad}]"
                node_outputs[nid] = [output_pad]

            if filter_str:
                filters.append(filter_str)
                
        return ";".join(filters)
