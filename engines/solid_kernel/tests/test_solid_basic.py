"""Tests for Solid Kernel scaffolding."""
import pytest
from engines.solid_kernel.service import SolidService
from engines.solid_kernel.schemas import AgentSolidInstruction

def test_solid_primitive():
    service = SolidService()
    
    # 1. Create Box
    instr = AgentSolidInstruction(
        op_code="PRIMITIVE",
        params={"kind": "BOX"}
    )
    result = service.execute_instruction(instr)
    
    assert result is not None
    assert result.id is not None
    assert result.history[0].op_code == "PRIMITIVE"

def test_solid_fillet():
    service = SolidService()
    solid = service.execute_instruction(AgentSolidInstruction(op_code="PRIMITIVE", params={"kind": "BOX"}))
    
    # 2. Fillet
    instr = AgentSolidInstruction(
        op_code="FILLET",
        params={
            "edge_indices": [1, 2],
            "radius": 0.5
        },
        target_id=solid.id
    )
    
    result = service.execute_instruction(instr)
    assert result is not None
    assert result.history[-1].op_code == "FILLET"
