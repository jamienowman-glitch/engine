"""Solid Service Stub (Precision Muscle) v1."""
from __future__ import annotations

import uuid
from typing import List, Dict, Any, Optional
from engines.solid_kernel.schemas import (
    SolidObject, AgentSolidInstruction, Point3,
    SolidPrimitiveType, ExtrudeOp, FilletOp, SolidBooleanOp, SolidBooleanType
)

from engines.solid_kernel.validation import validate_instruction

# Placeholder for OCCT/CadQuery/Manifold wrapper
# import OCP
# import build123d

class SolidService:
    """
    Stateful service for managing active solid sessions.
    Proxies to the robust kernel (C++/WASM).
    """
    
    def __init__(self):
        self._store: Dict[str, SolidObject] = {} # id -> Solid

    def execute_instruction(self, instruction: AgentSolidInstruction) -> Optional[SolidObject]:
        """
        The main entrypoint for Agents to drive the kernel.
        """
        # Validate
        context = None
        if instruction.target_id:
             context = self._store.get(instruction.target_id)
             
        validation = validate_instruction(instruction, context)
        if not validation.valid:
            # For V1, we print/log error and return None
            print(f"SolidKernel Validation Error: {validation.error}")
            return None

        op = instruction.op_code.upper()
        params = instruction.params
        target_id = instruction.target_id
        
        if op == "PRIMITIVE":
            return self._create_primitive(params.get("kind", "BOX"), params)
            
        if target_id and target_id in self._store:
            current_solid = self._store[target_id]
            
            if op == "EXTRUDE":
                extrude_op = ExtrudeOp(**params)
                return self._extrude(current_solid, extrude_op) # Usually consumes a sketch
                
            elif op == "FILLET":
                fillet_op = FilletOp(**params)
                return self._fillet(current_solid, fillet_op)
                
            elif op == "BOOLEAN":
                bool_op = SolidBooleanOp(**params)
                return self._boolean(bool_op)
                
        return None

    # --- Internal Handlers (To be implemented with OCCT/Manifold) ---

    def _create_primitive(self, kind: str, params: Dict[str, Any]) -> SolidObject:
        """Stub primitive creation."""
        # TODO: call Kernel.make_box(w, h, d)
        new_id = str(uuid.uuid4())
        
        solid = SolidObject(
            id=new_id,
            kernel_ref_id=f"memory://kernel_ptr_{new_id}",
            history=[AgentSolidInstruction(op_code="PRIMITIVE", params={"kind": kind}, target_id=new_id)],
            mass=1.0,
            volume=1.0,
            center_of_mass=Point3(x=0,y=0,z=0)
        )
        self._store[new_id] = solid
        return solid

    def _extrude(self, solid: SolidObject, op: ExtrudeOp) -> SolidObject:
        """Stub extrusion."""
        # In reality this takes a Sketch (2D) and returns a Solid.
        # Here we just mark history.
        solid.history.append(AgentSolidInstruction(op_code="EXTRUDE", params=op.model_dump(), target_id=solid.id))
        return solid

    def _fillet(self, solid: SolidObject, op: FilletOp) -> SolidObject:
        """Stub fillet."""
        solid.history.append(AgentSolidInstruction(op_code="FILLET", params=op.model_dump(), target_id=solid.id))
        return solid

    def _boolean(self, op: SolidBooleanOp) -> SolidObject:
        """Stub boolean."""
        # Consumes tool, modifies target.
        target = self._store.get(op.target_id)
        if target:
            target.history.append(AgentSolidInstruction(op_code="BOOLEAN", params=op.model_dump(), target_id=target.id))
            return target
        return None
