"""Tests for Catmull-Clark Subdivision."""
import pytest
from engines.mesh_kernel.service import MeshService
from engines.mesh_kernel.schemas import AgentMeshInstruction

def test_subd_increases_vertices():
    service = MeshService()
    
    # 1. Create Cube (8 verts, 6 faces)
    cube = service.execute_instruction(AgentMeshInstruction(op_code="PRIMITIVE", params={"kind": "CUBE"}))
    assert len(cube.vertices) == 8
    
    # 2. Subdivide 1 Level
    # For a cube, CC lvl 1:
    # 6 Face points
    # 12 Edge points
    # 8 Vertex points
    # Total = 26 vertices
    # Faces = 6 * 4 = 24 quads
    
    instr = AgentMeshInstruction(
        op_code="SUBDIVIDE",
        params={"iterations": 1},
        target_id=cube.id
    )
    
    subd_mesh = service.execute_instruction(instr)
    
    assert len(subd_mesh.vertices) == 26
    assert len(subd_mesh.faces) == 24
    assert "subdictions" not in subd_mesh.tags # just checking
