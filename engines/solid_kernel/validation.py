"""Solid Kernel Validation Logic."""
from __future__ import annotations
from typing import List, Optional
from engines.solid_kernel.schemas import AgentSolidInstruction, SolidObject

class ValidationResult:
    def __init__(self, valid: bool, error: Optional[str] = None):
        self.valid = valid
        self.error = error

def validate_instruction(instr: AgentSolidInstruction, context: Optional[SolidObject]) -> ValidationResult:
    """
    Validates if an instruction is semantically correct given the context.
    """
    op = instr.op_code.upper()
    params = instr.params
    
    if op == "PRIMITIVE":
        kind = params.get("kind")
        if not kind:
             return ValidationResult(False, "Missing 'kind' in PRIMITIVE params")
        if kind not in ["BOX", "CYLINDER", "SPHERE", "CONE"]:
             return ValidationResult(False, f"Unknown primitive kind: {kind}")
        # Check dims
        # TODO: Add specific checks for box (w,h,d), cylinder (r,h) etc.
        return ValidationResult(True)
        
    if op == "EXTRUDE":
        if not context:
            return ValidationResult(False, "EXTRUDE requires a target context")
        # Check sketch_id (in V1 we can't verify external sketch existence easily without registry)
        if "distance" not in params:
            return ValidationResult(False, "EXTRUDE requires 'distance'")
            
    if op == "FILLET":
        if not context:
            return ValidationResult(False, "FILLET requires a target context")
        edges = params.get("edge_indices")
        if not edges or not isinstance(edges, list):
            return ValidationResult(False, "FILLET requires 'edge_indices' list")
        if params.get("radius", 0) <= 0:
            return ValidationResult(False, "FILLET radius must be > 0")
            
    if op == "BOOLEAN":
        if not context:
             return ValidationResult(False, "BOOLEAN requires a target context")
        if "target_id" not in params and "tool_id" not in params: # Schema mismatch? 
            # Schema has target_id/tool_id in params. instr.target_id is the *modified* object.
            # Usually boolean merges tool INTO target.
            pass

    return ValidationResult(True)
