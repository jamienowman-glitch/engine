"""Tests for Mesh Kernel scaffolding."""
import pytest
from engines.mesh_kernel.service import MeshService
from engines.mesh_kernel.schemas import AgentMeshInstruction

def test_mesh_primitive():
    service = MeshService()
    
    # 1. Create Cube
    instr = AgentMeshInstruction(
        op_code="PRIMITIVE",
        params={"kind": "CUBE"}
    )
    result = service.execute_instruction(instr)
    
    assert result is not None
    assert result.id is not None
    assert len(result.vertices) == 8
    assert "primitive:cube" in result.tags

def test_mesh_sculpt():
    service = MeshService()
    mesh = service.execute_instruction(AgentMeshInstruction(op_code="PRIMITIVE", params={"kind": "SPHERE"}))
    
    # 2. Sculpt Move
    instr = AgentMeshInstruction(
        op_code="SCULPT",
        params={
            "brush": "MOVE",
            "center": {"x":0, "y":0, "z":0},
            "radius": 1.0,
            "strength": 0.5
        },
        target_id=mesh.id
    )
    
    result = service.execute_instruction(instr)
    assert result is not None
    assert "sculpt:MOVE" in result.tags
