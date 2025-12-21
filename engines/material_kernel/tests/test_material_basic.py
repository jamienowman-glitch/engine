"""Material Engine Tests."""
import pytest
from engines.material_kernel.service import MaterialService
from engines.material_kernel.schemas import AgentMaterialInstruction
from engines.mesh_kernel.schemas import MeshObject

def test_material_presets():
    service = MaterialService()
    assert "mat_clay" in service._library
    assert "mat_gold" in service._library
    assert service._library["mat_gold"].metallic == 1.0

def test_apply_material_global():
    service = MaterialService()
    # Mock Mesh
    mesh = MeshObject(
        id="m1",
        vertices=[[0,0,0], [1,0,0], [0,1,0]],
        faces=[[0,1,2]]
    )
    
    instr = AgentMaterialInstruction(
        op_code="APPLY_PRESET",
        params={"material_id": "mat_gold"},
        target_id="m1"
    )
    
    mat = service.execute_instruction(instr, target_mesh=mesh)
    
    assert mat is not None
    assert mat.name == "Gold"
    # Check mesh assignment
    assert "mat_gold" in mesh.material_groups
    assert 0 in mesh.material_groups["mat_gold"]
    assert "material:Gold" in mesh.tags

def test_paint_region():
    service = MaterialService()
    mesh = MeshObject(
        id="m2",
        vertices=[[0,0,0], [1,0,0], [0,1,0], [0,0,1]], # 4 verts
        faces=[[0,1,2], [0,2,3]] # 2 faces, idx 0 and 1
    )
    
    # Paint face 1 with Red Plastic
    instr = AgentMaterialInstruction(
        op_code="PAINT_REGION",
        params={
            "material_id": "mat_red_plastic",
            "face_indices": [1]
        },
        target_id="m2"
    )
    
    service.execute_instruction(instr, target_mesh=mesh)
    
    assert "mat_red_plastic" in mesh.material_groups
    assert 1 in mesh.material_groups["mat_red_plastic"]
    assert 0 not in mesh.material_groups["mat_red_plastic"]
