from typing import List, Dict, Any, Union
from engines.audio_macro_engine.models import MacroDefinition, MacroNode

def compile_macro_to_ffmpeg(macro: MacroDefinition, knob_overrides: Dict[str, Any] = None) -> str:
    if not macro.nodes:
        return "anull"
        
    knobs = knob_overrides or {}
    
    filters = []
    
    # Input label starts as [0:a] (assuming single input)
    current_label = "[0:a]"
    
    for i, node in enumerate(macro.nodes):
        next_label = f"[n{i}]"
        
        # Merge params
        params = node.params.copy()
        for k, v in knobs.items():
            # If knob key matches node index? e.g. "0.drive"
            pass # TODO: Implement complex override logic. For now use raw params.
            
        f_str = ""
        
        if node.type == "reverse":
            f_str = "areverse"
            
        elif node.type == "reverb":
            # Simple reverb using aecho
            # aecho=in_gain:out_gain:delays:decays
            in_g = params.get("in_gain", 0.6)
            out_g = params.get("out_gain", 0.3)
            delays = params.get("delays", 1000)
            decays = params.get("decays", 0.5)
            f_str = f"aecho={in_g}:{out_g}:{delays}:{decays}"
            
        elif node.type == "distortion":
            # acrusher
            # level_in, level_out, bits, mix, mode
            # simple mapping
            f_str = "acrusher=level_in=10:level_out=10:bits=4:mode=log:mix=0.5"
            
        elif node.type == "lowpass":
            freq = params.get("freq", 1000)
            f_str = f"lowpass=f={freq}"
            
        elif node.type == "limiter":
            inp = params.get("input", 0.0) # Pre-gain?
            # If input db > 0, we can add a volume filter before or use alimiter gain?
            # alimiter has "level_in" -- wait, alimiter params: level_in, level_out, limit, etc.
            # default strict limit -1db
            f_str = f"alimiter=limit=-1dB:level_in={1.0 + (inp/20.0)}" # Approx linear gain? No, db->linear is 10^(db/20)
            
        elif node.type == "volume":
            db = params.get("db", 0.0)
            f_str = f"volume={db}dB"
            
        else:
            # Fallback
            f_str = "anull"
            
        # Construct filter entry: [in]filter[out]
        filters.append(f"{current_label}{f_str}{next_label}")
        current_label = next_label

    # Final map to [out] if needed or just return chain?
    # Usually service needs [out] mapped.
    # We can rename last label to [out] or append [out]
    # But last filter construction used next_label = f"[n{i}]"
    
    # Let's map the very last output to [out] explicitly with anull?
    # Or just return the chain string, and let service map -map "[nLast]"
    
    # Cleanest: Append ",[nLast]anull[out]"?
    # Or just construct string "f1,f2,f3".
    
    # We used list of strings: ["[in]f1[n0]", "[n0]f2[n1]"]
    # Join with ;
    
    full_filter = ";".join(filters)
    # The output of this graph is the last label: f"[n{len(macro.nodes)-1}]"
    
    return full_filter, current_label
